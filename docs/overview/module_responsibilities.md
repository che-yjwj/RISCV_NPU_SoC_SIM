# Module Responsibilities  
**Path:** `docs/overview/module_responsibilities.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** System Architect  
**Last Updated:** YYYY-MM-DD  

---

## 1. 목적 (Purpose)

이 문서는 **NPU Simulator & Offline Compiler** 전체 시스템을 구성하는  
각 모듈의 **책임(Responsibility)**, **입출력(Inputs/Outputs)**, **경계(Does / Does Not)**를 명확히 정의한다.

목표는 다음과 같다.

- 모듈 간 역할을 명확히 분리하여 **Spec-Driven 개발**을 가능하게 한다.  
- 설계/구현/리팩토링 시, 각 모듈의 책임 범위를 명확히 인지할 수 있도록 한다.  
- 변경 시 영향 범위를 쉽게 파악할 수 있게 한다.

---

## 2. 상위 모듈 목록 (Top-Level Modules)

본 프로젝트는 크게 다음 모듈들로 구성된다.

1. **Host CPU (RISC-V)**
2. **Offline Compiler**
   - IRBuilder  
   - Quantization Annotator  
   - TilingPlanner  
   - SPMAllocator  
   - StaticScheduler  
   - CMDQGenerator  
3. **NPU Simulator Core**
   - ControlFSM  
   - CMDQExecutor  
   - DMAEngine  
   - TensorEngine(TE)  
   - VectorEngine(VE)  
   - MemoryModel(SPM/Bus/DRAM/NoC)  
   - TraceEngine  
4. **Visualization / Profiler**

이 문서에서는 각 모듈에 대해 **Input / Output / Does / Does Not** 관점으로 정의한다.

---

## 3. Host CPU (RISC-V)

### 3.1 역할 요약

| 항목         | 내용 |
|--------------|------|
| 이름         | Host CPU (RISC-V) |
| 타입         | Control / Driver |
| 주요 책임    | NPU launch, CMDQ 주소 설정, 결과 수집 |
| 직접 다루는 데이터 | CMDQ 메모리 포인터, CSR/MMIO 레지스터 |

### 3.2 Inputs

- Offline Compiler가 생성한 CMDQ (메모리 상 주소)
- 테스트/벤치마크 스크립트 (예: python, C harness)

### 3.3 Outputs

- NPU 실행 시작 신호 (`NPU_START` CSR/레지스터)
- CMDQ base address(`NPU_CMDQ_BASE`)
- 실행 완료 후: latency, 에러 코드, trace 파일 경로 등 (상위 앱으로 전달)

### 3.4 Does

- NPU 실행 시작/종료 제어  
- CMDQ base address / length 설정  
- 다수의 실험(모델/bitwidth/엔진 구성)을 시나리오 단위로 실행  

### 3.5 Does Not

- CMDQ 생성/변경을 하지 않는다.  
- NPU 내부 스케줄링/타일링/타이밍 모델을 변경하지 않는다.  
- TE/VE 연산 semantics를 이해할 필요가 없다.  

---

## 4. Offline Compiler

Offline Compiler는 IR 기반으로 **정적 스케줄 / CMDQ를 생성하는 전체 파이프라인**이다.  
하위 모듈별 책임을 명확히 분리한다.

---

### 4.1 IRBuilder

#### 4.1.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | IRBuilder |
| 책임      | ONNX → NPU IR 변환 (LayerIR / TensorIR) |
| 입력      | ONNX Graph |
| 출력      | NPU IR (Graph, TensorTable) |

#### 4.1.2 Does

- ONNX 노드를 NPU-friendly한 LayerIR로 변환 (GEMM, LN, QKV_PROJ, SOFTMAX 등)  
- TensorIR 생성 및 shape/layout propagation  
- 연산 fusion (예: MatMul + Add → GEMM+BIASED)  
- LLM 구조(Q/K/V, KV Cache 등)를 NPU IR 상에서 명시적으로 표현  

#### 4.1.3 Does Not

- 타일링 결정 (tile size, tile 수)을 하지 않는다.  
- SPM bank/offset을 할당하지 않는다.  
- TE/VE/TE_id/VE_id를 결정하지 않는다.  
- timing/latency 계산을 하지 않는다.

---

### 4.2 Quantization Annotator

#### 4.2.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | Quantization Annotator |
| 책임      | NPU IR에 W/A/KV bitwidth 설정을 주입 |
| 입력      | NPU IR (LayerIR), QConfig |
| 출력      | qbits_weight / qbits_activation / qbits_kv 가 주입된 NPU IR |

#### 4.2.2 Does

- 글로벌 기본 bitwidth(W/A/KV)를 LayerIR에 적용  
- per-layer override 정책(QConfig)을 IR에 반영  
- KV 전용 bitwidth를 attention/KV Cache 레이어에만 적용  

#### 4.2.3 Does Not

- 실제 quantization 연산(값의 scale/zero-point 처리)을 구현하지 않는다.  
- TE/VE/DMA 타이밍 계산을 하지 않는다.  
- SPM allocation이나 scheduling을 결정하지 않는다.

---

### 4.3 TilingPlanner

#### 4.3.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | TilingPlanner |
| 책임      | LayerIR → TileGraph로 분해 (tile 크기 및 구조 결정) |
| 입력      | Annotated NPU IR, 하드웨어 파라미터(SPM 용량, 엔진 개수 등) |
| 출력      | TileGraph (tile 단위 DAG) |

#### 4.3.2 Does

- 각 LayerIR에 대해 tile 단위 shape(M_tile, N_tile, K_tile 등)를 결정  
- bitwidth(qbits)에 따른 SPM 저장 크기를 고려  
- LLM에서는 head/seq 축 기준 tile을 정의  
- tile 간 의존성(데이터 플로우, partial sum 등)을 기본 그래프 형태로 표현  

#### 4.3.3 Does Not

- SPM bank/offset을 구체적으로 할당하지 않는다.  
- DMA 명령/주소를 생성하지 않는다.  
- TE/VE 스케줄링(엔진 배정, 순서)을 하지 않는다.

---

### 4.4 SPMAllocator

#### 4.4.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | SPMAllocator |
| 책임      | TileGraph의 각 tile에 대해 SPM bank/offset 할당 |
| 입력      | TileGraph, SPM 설정(num_banks, bank_size, port 등) |
| 출력      | SPM allocation 정보가 추가된 TileGraph |

#### 4.4.2 Does

- tile별 IFM/WGT/OFM/KV cache에 대해 bank index와 offset 결정  
- bitwidth에 기반한 실제 byte 크기 계산  
- bank conflict를 최소화하는 매핑 전략 탐색  
- multi-bank 구조에서 parallel access를 고려한 mapping  

#### 4.4.3 Does Not

- 타이밍/latency를 계산하지 않는다.  
- TE/VE 실행 순서를 계획하지 않는다.  
- CMDQ format을 정의하거나 생성하지 않는다.

---

### 4.5 StaticScheduler

#### 4.5.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | StaticScheduler |
| 책임      | TileGraph + SPM allocation + 엔진 자원 정보를 사용하여 정적 스케줄 생성 |
| 입력      | SPM 할당이 완료된 TileGraph, 엔진 구성(N_te, N_ve, DMA 채널 수 등) |
| 출력      | tile-level 스케줄 DAG (DMA/TE/VE 순서 + deps 정보) |

#### 4.5.2 Does

- tile 간 데이터 의존성(consumer/producer)을 고려해 실행 순서 결정  
- DMA → TE/VE → DMA 흐름 구성  
- multi-TE/VE에 대해 tile을 분배 (load-balance 전략)  
- `deps_before` 관계를 생성 (바로 CMDQ deps 필드로 전달 예정)  
- SPM reuse / bank conflict 완화 관점에서 순서를 조정  

#### 4.5.3 Does Not

- CMDQ JSON 포맷을 직접 생성하지 않는다.  
- 시뮬레이터 내부 TE/VE 구현 세부를 알 필요가 없다.  
- 실제 cycle 수를 계산하지 않는다 (이는 timing model + simulator의 역할).

---

### 4.6 CMDQGenerator

#### 4.6.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | CMDQGenerator |
| 책임      | 정적 스케줄 결과를 CMDQ(JSON 포맷)로 serialize |
| 입력      | 정적 스케줄 DAG, SPM allocation 정보, NPU IR |
| 출력      | CMDQ (DMA/TE/VE/SYNC 엔트리 리스트) |

#### 4.6.2 Does

- DMA_LOAD_TILE / DMA_STORE_TILE 엔트리 생성  
- TE_GEMM_TILE / VE_LAYERNORM_TILE / VE_SOFTMAX_TILE 등 생성  
- tile/엔진/주소/bitwidth 정보를 CMDQ 엔트리 필드에 매핑  
- `deps_before`를 CMDQ 엔트리 id 기반 배열로 변환  
- 마지막에 END opcode 추가  

#### 4.6.3 Does Not

- 스케줄을 변경하거나 tile 구성을 수정하지 않는다.  
- timing/latency를 계산하지 않는다.  
- TE/VE/DMA의 내부 동작을 시뮬레이션하지 않는다.

---

## 5. NPU Simulator Core

NPU Simulator Core는 CMDQ를 입력으로 받아 **cycle-based 실행**을 모사한다.

하위 모듈은 다음과 같다.

- ControlFSM  
- CMDQExecutor  
- DMAEngine  
- TensorEngine(TE)  
- VectorEngine(VE)  
- MemoryModel(SPM/Bus/DRAM/NoC)  
- TraceEngine  

---

### 5.1 ControlFSM

#### 5.1.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | ControlFSM |
| 책임      | CMDQ fetch/issue/종료 제어 |
| 입력      | CMDQ, 엔진 상태 (ready/busy, deps 완료 플래그) |
| 출력      | 각 엔진에 job issue, simulation 종료 신호 |

#### 5.1.2 Does

- CMDQ 엔트리를 순차 fetch  
- deps_before 조건 확인 (ready 여부 판단)  
- issue 가능한 엔트리를 해당 엔진 queue로 전달  
- END opcode를 만나면 시뮬레이션 종료  

#### 5.1.3 Does Not

- 각 엔진의 내부 timing/연산을 직접 수행하지 않는다.  
- SPM/DRAM 주소 계산을 하지 않는다 (CMDQ에 이미 준비되어 있음).  

---

### 5.2 CMDQExecutor

(실제 구현에서 ControlFSM과 통합 가능하지만, 논리적으로 분리해서 정의)

#### 5.2.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | CMDQExecutor |
| 책임      | CMDQ를 순회하며 issue 후보 관리 및 deps 상태 관리 |
| 입력      | CMDQ, 엔진 완료 이벤트 |
| 출력      | 각 엔진 job enqueue 요청, deps 완료 플래그 |

#### 5.2.2 Does

- CMDQ 엔트리별 state (not issued / issued / completed) 관리  
- deps_before/after 관계 추적  
- issue-ready인 엔트리를 ControlFSM에 알려줌  

#### 5.2.3 Does Not

- 실제 연산(계산/메모리 모사)을 수행하지 않는다.  
- timing을 결정하지 않는다.

---

### 5.3 DMAEngine

#### 5.3.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | DMAEngine |
| 책임      | DRAM ↔ SPM 간 데이터 이동에 대한 timing/bandwidth/traffic 모델링 |
| 입력      | DMA_LOAD_TILE / DMA_STORE_TILE CMDQ 엔트리 |
| 출력      | 완료 이벤트, DRAM traffic trace, SPM 접근 trace |

#### 5.3.2 Does

- `num_elements` + `qbits` → total_bytes 계산  
- bus width, burst size, contention 모델을 이용해 latency 계산  
- global cycle loop에서 per-cycle 진행 상태 업데이트  
- DRAM read/write bytes를 trace에 기록  

#### 5.3.3 Does Not

- TE/VE 연산을 수행하지 않는다.  
- 타일링/스케줄링을 변경하지 않는다.  
- CMDQ 구조를 수정하지 않는다.

---

### 5.4 TensorEngine (TE)

#### 5.4.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | TensorEngine (TE[i]) |
| 책임      | GEMM/Conv 등 tensor 연산의 tile-level timing 모델링 |
| 입력      | TE_GEMM_TILE 등 TE 관련 CMDQ 엔트리 |
| 출력      | 완료 이벤트, TE 활용도(trace), MAC ops 통계 |

#### 5.4.2 Does

- `m * n * k` → MAC ops 계산  
- 엔진 파라미터(MACs/cycle, pipeline depth)에 따른 latency 계산  
- busy/free 상태를 global cycle loop에서 갱신  
- tile-level 실행 start/end cycle trace 기록  

#### 5.4.3 Does Not

- 실제 수치 계산(값)을 수행할 필요는 없다 (참조용 값 계산은 별도 모듈에서 가능).  
- DMA/VE 연산을 대신하지 않는다.  
- CMDQ 스케줄/순서를 변경하지 않는다.

---

### 5.5 VectorEngine (VE)

#### 5.5.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | VectorEngine (VE[j]) |
| 책임      | LayerNorm/Softmax/GELU 등 벡터/element-wise 연산 timing 모델링 |
| 입력      | VE_LAYERNORM_TILE, VE_SOFTMAX_TILE 등 |
| 출력      | 완료 이벤트, VE 활용도(trace) |

#### 5.5.2 Does

- 연산 대상 길이(length)와 lanes count로 latency 추정  
- reduction, SFU 사용(exp, rsqrt 등)에 따른 추가 비용 반영  
- busy/free 상태 및 start/end cycle 기록  

#### 5.5.3 Does Not

- GEMM/Conv 등 TE의 역할을 대신하지 않는다.  
- DMA/메모리 관련 동작을 직접 수행하지 않는다.

---

### 5.6 MemoryModel (SPM/Bus/DRAM/NoC)

#### 5.6.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | MemoryModel |
| 책임      | SPM bank/port, bus/NoC bandwidth 및 contention 모델링 |
| 입력      | DMA/TE/VE에서 발생하는 메모리 접근 요청 |
| 출력      | access latency, conflict count, bandwidth usage |

#### 5.6.2 Does

- SPM bank mapping (address → bank)  
- bank/port conflict 시 stall 및 penalty 반영  
- Bus/NoC에 대한 aggregate bandwidth 계산  
- SPM/DRAM 접근을 trace로 기록  

#### 5.6.3 Does Not

- 타일링/스케줄링 결정에 직접 관여하지 않는다(단, 결과 분석에는 사용 가능).  
- CMDQ format을 변경하지 않는다.

---

### 5.7 TraceEngine

#### 5.7.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | TraceEngine |
| 책임      | 시뮬레이션 동안 발생하는 모든 이벤트를 trace 포맷으로 수집 |
| 입력      | DMA/TE/VE/ControlFSM/MemoryModel의 이벤트 |
| 출력      | trace 파일(JSON/CSV 등), summary metrics |

#### 5.7.2 Does

- per-engine timeline (start, end, opcode) 기록  
- per-window DRAM bandwidth usage 기록  
- SPM bank conflict count 기록  
- layer별 latency breakdown 생성  

#### 5.7.3 Does Not

- 직접 시각화(그래프)를 그리진 않는다 (Visualization 모듈에서 수행).  
- 스케줄/timing 결과에 영향을 주지 않는다.

---

## 6. Visualization / Profiler

### 6.1 역할 요약

| 항목      | 내용 |
|-----------|------|
| 이름      | Visualization / Profiler |
| 책임      | Trace를 시각화 및 통계 분석 |
| 입력      | Trace 파일, summary metrics |
| 출력      | Gantt chart, heatmap, utilization graph 등 |

### 6.2 Does

- Gantt timeline 생성  
- DRAM bandwidth heatmap 생성  
- TE/VE/DMA utilization bar/line chart 생성  
- bitwidth 변화에 따른 latency/traffic 비교 그래프 생성  

### 6.3 Does Not

- 스케줄/타일링/ISA를 변경하지 않는다.  
- CMDQ나 IR을 수정하지 않는다.  
- timing simulation을 직접 수행하지 않는다.

---

## 7. 모듈 간 의존성 규칙 (Dependency Rules)

### 7.1 방향성 규칙

- Offline Compiler → NPU Simulator (단방향)  
- NPU Simulator → Visualization (단방향)  
- Host CPU → NPU Simulator (launch-only)  

즉,

- Compiler는 Simulator를 참조하지 않고,  
- Simulator는 Compiler의 산출물(CMDQ)만 사용한다.  
- Visualization은 Simulator 결과(trace)만 사용한다.

### 7.2 변경 영향 범위

- IRBuilder 변경 → TilingPlanner, Scheduler, CMDQGenerator, Simulator까지 영향 가능  
- TilingPlanner 변경 → SPMAllocator, Scheduler, CMDQGenerator에 영향  
- CMDQ 포맷 변경 → Simulator, TraceEngine, Visualization 모두 영향  
- Timing 모델 변경(DMA/TE/VE/MemoryModel) → 결과 latency/trace는 변하지만, Compiler에는 영향 없음  

---

## 8. 정리 (Summary)

이 문서는 각 모듈에 대해 다음 네 가지 관점으로 책임을 정의했다.

1. **Input**: 어떤 데이터를 받아들여  
2. **Output**: 어떤 산출물을 만들어내며  
3. **Does**: 실제로 수행해야 하는 일은 무엇이고  
4. **Does Not**: 절대 해서는 안 되는 일(다른 모듈 책임)은 무엇인지

이 정의를 통해:

- 모듈 경계를 명확히 하고  
- Spec-Driven Development를 유지하며  
- 리팩토링/확장 시에 영향 범위를 쉽게 파악할 수 있다.

앞으로 새로운 모듈이 추가되거나 기존 모듈이 세분화될 경우,  
반드시 이 문서에 해당 모듈의 책임을 먼저 정의한 뒤 구현을 진행해야 한다.
