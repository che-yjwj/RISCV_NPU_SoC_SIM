# Offline Compiler Design
**Path:** `docs/design/offline_compiler_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-04

---

## 1. 목적
Offline Compiler는 ONNX 모델과 하드웨어 설정을 입력으로 받아 **NPU IR → TileGraph → SPM allocation → Static Schedule → CMDQ**를 생성하는 파이프라인이다.  
이 문서는 상위 흐름과 각 서브모듈의 연결 관계를 정의한다.

관련 스펙:
- `docs/overview/system_architecture.md`
- `docs/overview/dataflow_overview.md`
- `docs/spec/ir/*.md`
- `docs/spec/isa/*.md`
- `docs/spec/timing/*.md`
- `docs/spec/quantization/*.md`

## 2. 책임
- **입력**
  - ONNX 모델 파일 또는 in-memory graph.
  - 하드웨어 config (엔진 수, SPM 용량, DRAM/Bus, bitwidth 허용 등).
  - Quantization 정책(QConfig).
- **출력**
  - CMDQ JSON (시뮬레이터 입력).
  - Optional: NPU IR, TileGraph, SPM allocation, Schedule snapshot.
- **주요 역할**
  - IRBuilder: ONNX → NPU IR 변환.
  - Quantization Annotator: qbits W/A/KV 주입.
  - TilingPlanner: tile 크기/개수 결정 및 TileGraph 생성.
  - SpmAllocator: tile별 SPM bank/offset 할당.
  - StaticScheduler: DMA/TE/VE tile-level 순서+deps 결정.
  - CmdqGenerator: 위 결과를 CMDQ JSON으로 serialize.
- **하지 말아야 할 일**
  - 시뮬레이터 동작/타이밍 계산.
  - 런타임 제어(Host CPU 쪽 로직).

## 3. 내부 구조

### 3.1 모듈 분할
- `OfflineCompiler` (파사드)
  - `IrBuilder`
  - `QuantizationAnnotator`
  - `TilingPlanner`
  - `SpmAllocator`
  - `StaticScheduler`
  - `CmdqGenerator`

### 3.2 데이터 플로우
```text
ONNX → IrBuilder → NPU IR
      → QuantizationAnnotator → Annotated IR
      → TilingPlanner → TileGraph
      → SpmAllocator → TileGraph + SPM map
      → StaticScheduler → tile-level schedule DAG
      → CmdqGenerator → CMDQ(JSON)
```

### 3.3 Pass Graph (개념도)

Offline Compiler는 여러 pass를 거치며 그래프를 점진적으로 변환한다.  
아래는 노드=pass, 엣지=데이터 흐름을 단순화한 pass graph이다.

```text
ONNX Model
   |
   v
[IrBuilder]
   |
   v
[QuantizationAnnotator]
   |
   v
[TilingPlanner] ---> [SpmAllocator] ---> [StaticScheduler] ---> [CmdqGenerator]
                                              |                      |
                                              +------>  CMDQ JSON <--+
```

특징:
- 앞단은 모델 표현(NPU IR + quantization)을 만드는 logical pass.
- 뒷단은 하드웨어 자원(SPM/엔진)을 고려한 타일/스케줄/CMDQ pass.
- 향후 최적화 pass(예: fusion, reordering)는 위 graph 사이/위에 추가 가능하다.

## 4. 알고리즘 / 플로우

### 4.1 상위 run 메서드 예시
```python
def compile(onnx_path: str, hw_config: HwConfig, qconfig: QConfig) -> CmdqArtifact:
    ir = IrBuilder.build(onnx_path)
    ir = QuantizationAnnotator.annotate(ir, qconfig)
    tile_graph = TilingPlanner.plan(ir, hw_config.spm, hw_config.engines)
    tile_graph = SpmAllocator.allocate(tile_graph, hw_config.spm)
    schedule = StaticScheduler.schedule(tile_graph, hw_config.engines)
    cmdq = CmdqGenerator.generate(schedule, tile_graph, ir, hw_config)
    return CmdqArtifact(cmdq=cmdq, ir=ir, tile_graph=tile_graph, schedule=schedule)
```

## 5. 인터페이스
- `OfflineCompiler.compile(onnx_model, hw_config, qconfig) -> CmdqArtifact`
- 각 서브모듈은 `docs/design/ir_builder_design.md` 등에서 상세 정의.

구성 파라미터:
- optimization level (타일링 aggressiveness, scheduling heuristics).
- debug 옵션(중간 결과 dump 여부).

## 6. 예시 시나리오
- Small MLP/Transformer block에 대해:
  - ONNX → CMDQ까지의 결과를 모두 저장하여 시뮬레이터와 trace를 비교.
  - 특히 하나의 FFN 또는 Attention block을 선택해:
    - NPU IR (layer/op 구조)
    - TileGraph (tile 분해)
    - SPM allocation (bank/offset)
    - Schedule DAG (tile 순서/엔진 할당)
    - CMDQ(JSON) (실행 스트림)
    를 한 세트의 “golden 파이프라인 예제”로 유지하면, 설계 변경/회귀 테스트 기준점으로 활용할 수 있다.

## 7. 향후 확장
- MLIR backend 연동.
- auto-tuning 기반 tile/schedule search.
- profile-guided compilation (이전 trace를 사용해 스케줄 개선).

## 8. 부록 A — Lowering 규칙 레퍼런스
Offline Compiler는 `CmdqGenerator` 단계에서 IR/TileGraph 노드를 CMDQ/ISA stream으로 변환할 때 **일관된 로워링 규칙**을 따라야 한다.  
규칙의 풀 버전은 아래 참고 문서에 정리되어 있으며, 이 문서는 핵심 요약본을 제공한다.

- 주요 참고 문서  
  - `docs/references/p2_riscv_npu/lowering_rules_tensor_ops_full.md` — MatMul/Conv/FFN/LN/Softmax/GELU 등 일반 Tensor 연산 규칙  
  - `docs/references/p2_riscv_npu/lowering_rules_kv_attention_full.md` — KV Cache 기반 Attention 전체 시퀀스

### 8.1 공통 패턴 요약
| IR TileOp | 필수 CMDQ 시퀀스 (요약) | 비고 |
| --- | --- | --- |
| MatMul / Conv (im2col) | `DMA_LOAD_TILE (IFM/WGT)` → `SYNC_WAIT` → `TE_MATMUL_TILE` → `SYNC_WAIT` → `DMA_STORE_TILE` | partial-sum 모드 시 TE accumulate flag 사용 |
| FFN 1st MatMul + Bias + GELU | `LOAD X/W1/B1` → `TE_MATMUL_TILE` → `VE_ADD_TILE` → `VE_GELU_TILE` | Bias/GELU는 VE 타일 |
| FFN 2nd MatMul | `LOAD W2` → `TE_MATMUL_TILE` → `DMA_STORE_TILE` | |
| LayerNorm / RMSNorm | `LOAD X` → `VE_RMSNORM_TILE` → `STORE Y` | |
| Softmax | `LOAD Scores` → `VE_SOFTMAX_TILE` → `STORE` | |
| GELU | `LOAD` → `VE_GELU_TILE` → `STORE` | |

### 8.2 KV-Attention 로워링 요약
하나의 timestep에 대해 생성되는 대표 CMDQ 시퀀스:

1. **Q/K/V Projection**  
   `DMA_LOAD_TILE (X/Wq)` → `TE_MATMUL_TILE (Q)` → … → `TE_MATMUL_TILE (V)`  
2. **KV Store**  
   `KV_STORE_TILE head, spmK/V` (Prefill/Decode 공통)  
3. **KV Load (Decode 시)**  
   `KV_LOAD_TILE spmKall/Vall, head, kv_range_desc`  
4. **Attention Score 및 Softmax**  
   `TE_QKT_TILE`, `VE_SOFTMAX_TILE`  
5. **Attn·V 및 Output Projection**  
   `TE_AV_TILE`, `TE_MATMUL_TILE (output)` → `DMA_STORE_TILE`

필수 Sync 규칙:
- `DMA_LOAD_TILE → TE/VE`  
- `KV_STORE_TILE → KV_LOAD_TILE` (head/seq 순서 보장)  
- `TE_QKT_TILE → VE_SOFTMAX_TILE → TE_AV_TILE`  
- `TE_AV_TILE → TE_MATMUL_TILE (output)` → `DMA_STORE_TILE`

### 8.3 Offline Compiler 연계 지침
- `CmdqGenerator`는 IR/TileGraph의 op tag를 기준으로 위 표의 시퀀스를 template화하여 emit한다.
- KV-aware lowering 시 `cmdq_entry.details.tensor_role`, `head_id`, `kv_range_desc` 등을 채워야 하며, 스케줄러가 삽입한 deps를 유지한다.
- 향후 새로운 op가 추가되면 참조 문서에 규칙을 정의하고, 부록을 갱신해 개발자들이 빠르게 확인할 수 있도록 한다.
