# NPU-IR Lowering & Execution Specification
## npu_ir_lowering_and_execution.md

Author: ChatGPT (for 창훈)
Reference: PyTorchSim TOG (PSAL-POSTECH)
Target: Static-scheduled Mobile / Edge NPU Simulator & Compiler

---

## 0. Scope

본 문서는 NPU-IR(Core Spec)에 정의된 구조를
실제 실행 가능한 형태로 변환하는 과정인
Lowering 및 Execution Semantics를 정의한다.

대상은 다음 세 계층이다.

- Compiler Backend (IR → Descriptor)
- Simulator Backend (TLS / Global-cycle)
- Hardware Command Interface (CMDQ / MMIO)

---

## 1. Lowering Overview

Lowering은 다음 단계를 따른다.

1. NPU-IR 구조 검증 (정적)
2. Loop 구조 분석 및 core partition 결정
3. AddressExpr 해석 및 주소 결정
4. DMA / Compute 노드의 Descriptor 변환
5. Core별 Command Stream 생성

Lowering 결과는
“실행 순서가 완전히 결정된 Descriptor Stream”이다.

---

## 2. IR → CMDQ / Descriptor Mapping

아래 표는 NPU-IR 노드와 하드웨어 인터페이스 간의
1:1 의미 매핑을 정의한다.

Mapping Table:

IR Node Type        →  Backend Descriptor
------------------------------------------------
DmaLoad             →  DMA_DESC(load)
DmaStore            →  DMA_DESC(store)
DmaWait             →  BARRIER / FENCE
ComputeTile (TE)    →  TE_DESC
ComputeTile (VE)    →  VE_DESC
ComputeTile (SPARSE)→  SPARSE_DESC

Descriptor는 다음 정보를 반드시 포함해야 한다.

- 대상 엔진 ID (TE / VE / DMA channel)
- 주소 정보 (base, stride, bytes)
- Tag (emit / wait)
- 예상 실행 latency (TLS 기준)

---

## 3. Static Core Partitioning

### 3.1 Partition 기준

Static partitioning은
가장 바깥쪽 LoopBegin 중
loop_type = PARALLEL 인 루프를 기준으로 수행한다.

예시:

- LoopBegin(loop_type = PARALLEL, iter = 0..127)
- num_cores = 8

→ 각 core는 16 iteration을 정적으로 할당받는다.

---

### 3.2 Partition 정책

두 가지 정책을 정의한다.

1. Contiguous Partition
- 각 core가 연속된 iteration 범위를 담당
- 장점: 주소 locality 우수
- 단점: iteration별 cost 편차에 취약

2. Block-Cyclic Partition
- iteration을 core에 round-robin 분배
- 장점: load imbalance 완화
- 단점: 주소 locality 저하 가능

정책 선택은 컴파일 타임 또는 실험 설정으로 결정한다.

---

## 4. Command Stream Construction

### 4.1 Per-Core Stream

Lowering 결과는 core별 독립된 command stream이다.

- 각 core는 동일한 IR 구조를 공유
- loop iteration 범위만 다르게 설정됨
- core 간 runtime synchronization은 없음 (정적)

---

### 4.2 Ordering Rules

Command stream 내에서는 다음 규칙을 따른다.

1. CONTROL edge → 명시적 순서
2. DATA edge → producer 이후 consumer
3. EVENT edge → Tag emit 이후 wait

암묵적 순서는 존재하지 않는다.

---

## 5. Address Resolution

### 5.1 AFFINE Address Resolution

AFFINE AddressExpr는
loop index를 이용해 주소를 계산한다.

의사 코드:

  addr = base
  for each term:
    addr += loop_index[term.loop_id] * term.stride

이 계산은 컴파일 타임 또는
시뮬레이터 실행 시점에 수행된다.

---

### 5.2 INDIRECT Address Resolution

INDIRECT AddressExpr는
SPM에 적재된 index buffer를 참조한다.

특징:

- KV-cache, sparse attention에 사용
- Address dependency가 runtime에 결정됨
- Lowering 시 index_ref의 lifetime 검증 필요

---

## 6. Tag Handling & Synchronization

### 6.1 Tag Emit

- DmaLoad / DmaStore는 completion 시 Tag를 emit
- Tag는 전역 event로 기록됨

---

### 6.2 DmaWait Semantics

DmaWait는 다음 의미를 갖는다.

- wait_tags의 모든 Tag가 완료될 때까지 stall
- mode = ALL 만 허용 (정적 모델 단순화)

Lowering 시 DmaWait는
하드웨어 BARRIER 또는
시뮬레이터 event-wait로 변환된다.

---

## 7. Execution Models

### 7.1 Tile-Level Simulation (TLS)

TLS의 핵심 가정:

- ComputeTile.cycles 는 고정값
- Compute는 deterministic
- DMA / NoC / DRAM만 contention을 모델링

실행 흐름:

- Descriptor issue
- Resource availability 확인
- cycles만큼 시간 진행
- completion event 기록

TLS는 빠른 DSE에 적합하다.

---

### 7.2 Global Cycle Simulation

Global-cycle 모델은
모든 자원을 하나의 timebase에서 모델링한다.

특징:

- CPU / DMA / TE / VE가 동일한 global clock 사용
- ComputeTile은 내부 micro-event로 분해 가능
- queue depth, pipeline stall 분석 가능

단점:

- 구현 복잡도 증가
- 시뮬레이션 속도 저하

---

## 8. Validation Rules (Mandatory)

Lowering 전에 다음 검증을 반드시 수행해야 한다.

1. LoopBegin / LoopEnd 스택 정합성
2. Tag uniqueness (중복 emit 금지)
3. 모든 DmaWait는 대응되는 Tag emit 보장
4. SPM capacity 초과 금지
5. TE tile_shape ≤ HwProfile.te_shape
6. VE vector length ≤ HwProfile.ve_lanes

검증 실패 시 Lowering은 중단되어야 한다.

---

## 9. Typical Lowering Flow (Summary)

1. Parse NPU-IR
2. Validate structure & resources
3. Determine core partition
4. Resolve addresses
5. Generate per-core descriptor stream
6. Execute in TLS or Global-cycle backend

---

## 10. Notes

- 본 문서는 “실행 의미”를 정의한다.
- 성능 모델 파라미터는 별도 timing spec에서 정의한다.
- Prefill / Decode 분리는 workload 레벨에서 표현한다.
