# Golden Trace Examples
**Path:** `docs/test/golden_trace_examples.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
회귀(regression) 검증을 위해 **대표적인 workload들에 대한 참조 trace(golden)**를 정의하고 관리 방법을 규정한다.

## 2. 범위
- 포함:
  - MLP/Conv/Attention/LLM 블록 등 대표적인 실행 패턴.  
  - 주요 하드웨어/bitwidth 조합(예: 2TE+2VE, W4A8, KV4 등).  
- 제외:
  - 모든 가능한 모델/구성(대표 샘플만 선정).

## 3. Golden 시나리오 예시
| ID        | 워크로드         | 설명                               | 아티팩트 위치                          |
|-----------|------------------|------------------------------------|----------------------------------------|
| GT-MLP-01 | Small MLP        | feed-forward network               | `tests/golden/trace/mlp_small.json`    |
| GT-CONV-01| ConvNet          | Conv+Pool 조합                     | `tests/golden/trace/conv_small.json`   |
| GT-ATTN-01| Self-Attention   | 단일 Attention 블록               | `tests/golden/trace/attn_block.json`   |
| GT-LLM-01 | LLM Prefill/Decode | 짧은 시퀀스 LLM 실행             | `tests/golden/trace/llm_short.json`    |

### 3.1 LLaMA Prefill/Decode Golden 예시 (GT-LLM-01)
`llama_attention_timeline_full.md`, `llama_attention_isa_stream_full.md`를 기반으로 한 trace 예시는 다음을 포함한다.

- **Prefill CMDQ 흐름**:  
  `DMA_LOAD_TILE(X)` → `TE_MATMUL_TILE(Q/K/V)` → `KV_STORE_TILE` → `TE_QKT_TILE` → `VE_SOFTMAX_TILE` → `TE_AV_TILE` → `TE_MATMUL_TILE` → `DMA_STORE_TILE`.  
  trace에서는 DMA/TE/VE/KV 이벤트가 phase=`PREFILL`로 표시된다.

- **Decode CMDQ 흐름(토큰 루프)**:  
  `KV_LOAD_TILE(K_all/V_all)` → `TE_QKT_TILE` → `VE_SOFTMAX_TILE` → `TE_AV_TILE` → `TE_MATMUL_TILE` → `DMA_STORE_TILE`.  
  `TOKEN_EVENT`의 `token_index`와 `phase="DECODE"`를 사용해 토큰별 latency를 측정한다.

### 3.2 Spec/Design ↔ Golden ID 매핑 표

각 항목은 trace_format_spec에 맞춘 단일 JSON 파일로 관리한다.

### 3.2 Spec/Design ↔ Golden ID 매핑 표

| Golden ID | Spec 문서 | Design 문서 |
| --- | --- | --- |
| GT-MLP-01  | `docs/spec/trace/trace_format_spec.md` | `docs/overview/system_architecture_overview.md`, `docs/design/npu_simulator_core_design.md` |
| GT-CONV-01 | `docs/spec/trace/trace_format_spec.md` | `docs/design/dma_engine_design.md`, `docs/design/te_engine_design.md` |
| GT-ATTN-01 | `docs/spec/trace/trace_format_spec.md`, `docs/overview/dataflow_overview.md` | `docs/design/ir_builder_design.md`, `docs/design/static_scheduler_design.md` |
| GT-LLM-01  | `docs/spec/trace/trace_format_spec.md`, `docs/spec/trace/gantt_timeline_spec.md`, `docs/spec/quantization/kv_cache_quantization_spec.md` | `docs/design/npu_simulator_core_design.md`, `docs/design/visualizer_design.md` |

### 3.3 최소 비교 필드 예시

Golden trace 비교 시 기본적으로 확인해야 할 필드는 다음과 같다.

| 범주 | 필드 예시 | 설명 |
| --- | --- | --- |
| 요약 메트릭 | `summary_metrics.cycles_total` | 총 cycle 수 |
|  | `summary_metrics.dram_bytes_read/write` | DRAM 트래픽 합계 |
| TE/VE 타임라인 | `timeline_events[ENGINE_EVENT].engine`/`engine_id` | 엔진별 실행 순서 |
|  | `start_cycle`, `end_cycle` | 주요 tile 실행 구간 |
| DMA/메모리 | `details.bytes`, `details.tensor_role` | tile별 전송 크기/역할 |
| 토큰/페이즈 | `TOKEN_EVENT.phase`, `token_index` | Prefill/Decode 경계 및 token별 latency |

간단한 비교 로직 예:
- 필수 필드 값이 정확히 일치하는지 확인.  
- cycle/bytes 등 연속 값은 성능 검증 프로토콜에서 정의한 허용 오차 범위 내 diff만 허용.

## 4. 절차 / 자동화
- golden 생성:
  1. 신뢰할 수 있는 버전의 컴파일러/시뮬레이터로 실행.  
  2. Trace 결과를 검토/승인 후 `tests/golden/trace/`에 저장.  
- 회귀 검증:
  - `tests/regression/test_golden_trace.py`에서 현재 trace와 golden trace를 비교.  
  - 허용 오차 범위(예: latency ±1%, BW ±1%) 내에서 diff 허용.

## 5. 데이터 / 아티팩트 관리
- 저장 위치:
  - `tests/golden/trace/*.json`  
  - 필요 시 요약 CSV/메타데이터(`tests/golden/trace_index.yaml`) 추가.  
- 변경 정책:
  - golden 업데이트는 반드시 PR에서 “왜 변경되었는지” 설명과 함께 리뷰/승인 필요.

## 6. 리뷰 / 승인 기준
- golden 파일 변경 시:
  - [ ] 관련 spec/design/test 문서에서 변경 이유가 설명되어 있는가?  
  - [ ] 기존 버전과 비교한 diff(주요 metric) 요약이 있는가?  
  - [ ] 변경이 의도된 regression이 아닌지 확인했는가?

## 7. 향후 확장
- 다양한 시나리오(긴 시퀀스, 다양한 KV bitwidth, multi-TE/VE config) 추가.  
- Golden trace 압축/샤딩 전략 도입(파일 수가 많아질 경우).  
