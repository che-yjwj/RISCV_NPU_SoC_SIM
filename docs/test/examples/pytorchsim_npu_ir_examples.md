# NPU-IR Canonical Examples
## npu_ir_examples.md

Author: ChatGPT (for 창훈)
Reference: PyTorchSim TOG (PSAL-POSTECH)
Target: Static-scheduled Mobile / Edge NPU Simulator & Compiler

---

## 0. Purpose

본 문서는 NPU-IR Core Spec과 Lowering & Execution Spec에서 정의한
개념을 **실행 가능한 예제 형태**로 정리한다.

관련(메인 스펙 체크리스트):
- [tile_semantics_validation_checklist.md](../../spec/trace/tile_semantics_validation_checklist.md)

모든 예제는 다음 목적을 가진다.

- IR 구조의 정형적 사용법 제시
- 정적 스케줄링 NPU에서의 현실적인 패턴 반영
- PyTorchSim TOG와의 개념적 대응 확인
- Simulator / Compiler 구현 시 기준(reference) 제공

---

## 1. Example A — GEMM Tile (TE-Centric)

### 1.1 Problem Setting

- Matrix A: [512 x 64]
- Matrix B: [64 x 64]
- Matrix C: [512 x 64]
- Tile size: 64 x 64 x 64
- Execution style: Static, PARALLEL loop

---

### 1.2 High-Level Execution Pattern

```text
for m_tile in 0..7 (PARALLEL):
  DMA load A_tile[m]
  DMA load B_tile
  wait for A_tile[m], B_tile
  TE compute C_tile[m] = A_tile[m] @ B_tile
  DMA store C_tile[m]
```

---

### 1.3 NPU-IR Representation

```yaml
LoopBegin:
  loop_id: 0
  loop_type: PARALLEL
  iter_begin: 0
  iter_end: 8
  iter_step: 1

DmaLoad:
  src: A (DRAM)
  dst: A_tile (SPM)
  bytes: 8192
  addr:
    kind: AFFINE
    base: A_base
    terms:
      - loop_id: 0
        stride: 8192
  tag: A_tile_m

DmaLoad:
  src: B (DRAM)
  dst: B_tile (SPM)
  bytes: 8192
  addr:
    kind: AFFINE
    base: B_base
    terms:
      - loop_id: 0
        stride: 0
  tag: B_tile

DmaWait:
  wait_tags: [A_tile_m, B_tile]
  mode: ALL

ComputeTile:
  engine: TE
  cycles: 320
  inputs: [A_tile, B_tile]
  outputs: [C_tile]
  kernel_meta:
    op: matmul
    tile_shape: [64, 64, 64]
    dtype: f16

DmaStore:
  src: C_tile (SPM)
  dst: C (DRAM)
  bytes: 8192
  addr:
    kind: AFFINE
    base: C_base
    terms:
      - loop_id: 0
        stride: 8192
  tag: C_tile_m

LoopEnd:
  loop_id: 0
```

---

### 1.4 Architectural Interpretation

- PARALLEL loop은 core 단위로 분할됨
- B_tile은 read-only, 재사용 가능
- A_tile / C_tile은 iteration별 독립
- Compute latency는 deterministic (TLS-friendly)

---

## 2. Example B — LLaMA Decode Attention (KV Cache, VE-Centric)

### 2.1 Problem Setting

- Decode stage (1 token)
- KV-cache length: 128
- Head dimension: 64
- Data type: int8 (KV), accumulation in i32
- Execution style: ACCUMULATION loop

---

### 2.2 High-Level Execution Pattern

```text
for i in 0..127 (ACCUMULATION):
  DMA load K_i from KV-cache
  wait for K_i
  VE compute score_i = dot(Q, K_i)

VE compute:
  softmax(scores)
  weighted sum with V
```

---

### 2.3 NPU-IR Representation

```yaml
LoopBegin:
  loop_id: 0
  loop_type: ACCUMULATION
  iter_begin: 0
  iter_end: 128
  iter_step: 1

DmaLoad:
  src: K_cache (DRAM)
  dst: K_i (SPM)
  bytes: 1024
  addr:
    kind: AFFINE
    base: K_cache_base
    terms:
      - loop_id: 0
        stride: 1024
  tag: K_i_tag

DmaWait:
  wait_tags: [K_i_tag]
  mode: ALL

ComputeTile:
  engine: VE
  cycles: 40
  inputs: [Q, K_i]
  outputs: [score_i]
  kernel_meta:
    op: dot
    tile_shape: [64]
    dtype: int8_to_i32

LoopEnd:
  loop_id: 0

ComputeTile:
  engine: VE
  cycles: 60
  inputs: [scores]
  outputs: [attn_out]
  kernel_meta:
    op: softmax_reduce_weighted_sum
    tile_shape: [128]
    dtype: i32_to_f16
```

---

### 2.4 Architectural Interpretation

- ACCUMULATION loop은 순차 실행
- KV-cache는 DRAM-bound
- VE가 latency-critical path
- DMA latency hiding이 제한적 (decode 특성)

---

## 3. Example C — Prefill KV Store (Write-Dominant)

### 3.1 Problem Setting

- Prefill stage
- Sequence length: 128
- Tile size: 64
- Execution style: PARALLEL loop
- Operation: Q/K/V projection + KV-cache write

---

### 3.2 High-Level Execution Pattern

```text
for t in 0..127 (PARALLEL):
  TE compute K_tile, V_tile
  DMA store K_tile → KV-cache
  DMA store V_tile → KV-cache
```

---

### 3.3 NPU-IR Representation

```yaml
LoopBegin:
  loop_id: 0
  loop_type: PARALLEL
  iter_begin: 0
  iter_end: 128
  iter_step: 1

ComputeTile:
  engine: TE
  cycles: 300
  inputs: [X_tile, Wk]
  outputs: [K_tile]
  kernel_meta:
    op: matmul
    tile_shape: [64, 64, 64]
    dtype: f16

DmaStore:
  src: K_tile (SPM)
  dst: K_cache (DRAM)
  bytes: 8192
  addr:
    kind: AFFINE
    base: K_cache_base
    terms:
      - loop_id: 0
        stride: 8192
  tag: K_store_tag

LoopEnd:
  loop_id: 0
```

---

### 3.4 Architectural Interpretation

- Prefill은 write-heavy workload
- PARALLEL loop으로 throughput 극대화
- Decode 단계와 메모리 접근 패턴이 완전히 다름
- KV-cache layout 설계가 성능에 직접적 영향

---

## 4. Cross-Example Insights

| Aspect        | GEMM            | Decode Attention | Prefill KV |
|--------------|-----------------|------------------|------------|
| Dominant Eng | TE              | VE               | TE         |
| Loop Type    | PARALLEL        | ACCUMULATION     | PARALLEL  |
| Memory Bound | Medium          | High (DRAM)      | Medium    |
| Latency Crit | Compute         | Memory           | Compute   |

---

## 5. Final Notes

- 본 예제들은 IR 설계의 “정답 패턴”이다.
- 실제 모델은 이들의 조합으로 표현된다.
- Simulator 검증 시 regression reference로 사용 권장.

---

## 6. Determinism Guarantees (권고)

아래 항목들은 시뮬레이터/컴파일러가 결과를 재현 가능하게 만들기 위한
최소 결정성 규칙이다.

- 동일 입력 IR은 동일한 타일/태스크 실행 순서를 가져야 한다 (랜덤 금지)
- 모든 동기화는 명시적이어야 한다 (Tag emit/wait 또는 TDG dependency)
- DRAM 접근은 `DmaLoad/DmaStore`로만 표현되어야 한다
- 타일 payload는 Global SRAM/SPM에 상주하고, 엔진은 이를 load/store로만 접근한다
- TE→VE handoff는 STB(디스크립터 스트림)로만 모델링한다

---

## 7. Simulator Validation Checklist (요약)

다음 항목은 예제 기반으로 빠르게 구현 정확도를 검증하기 위한 체크리스트이다.

- Tile lifetime: allocate/produce/handoff/consume/free 순서 위반이 없어야 한다
- Global SRAM: 점유(바이트/타일 수) 추적과 초과 시 stall/실패 처리가 있어야 한다
- STB: payload 없이 디스크립터만 전달하고 ready/valid/back-pressure를 모델링해야 한다
- Prefill→Decode 전환: KV cache는 DRAM에 영속 저장되고, Decode에서는 Time_tile 단위로 staging되어야 한다
- Decode 모델: KV 타일 DMA prefetch와 TE/VE 연산이 중첩될 수 있어야 하며, stall 원인이 trace로 남아야 한다

간단 타임라인 예시(개념):

```text
Cycle →
DMA_LOAD(KV_tile) ───┐
                      ├─ overlap
TE/VE compute(tile)   ┘
```
