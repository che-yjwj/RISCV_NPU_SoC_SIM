# Offline Compiler Design
**Path:** `docs/design/offline_compiler_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

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
