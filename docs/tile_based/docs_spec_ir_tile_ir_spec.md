# Tile IR Specification (TileDesc 기반 NPU-IR 확장)

## 1. 문서 목적
본 문서는 TileRT 개념을 기반으로 **Tile 단위 실행을 1급 시민(first-class object)**으로 취급하는 NPU-IR 확장을 정의한다. 본 IR은 스케줄링 객체이자 실행 객체이며, cycle-based NPU 시뮬레이터 및 향후 Tile-first ISA 설계의 기준 스펙으로 사용된다.

---

## 2. 설계 원칙

### 2.1 IR의 역할 재정의
기존 IR: 연산을 "무엇을 실행할 것인가" 중심으로 표현

Tile IR: 실행을 "언제, 무엇을, 어떤 자원에서 실행할 것인가"까지 포함

즉, Tile IR은 **명령어 나열이 아니라 실행 DAG의 명세**이다.

---

### 2.2 Tile은 명령어가 아니다
Tile은 다음 성격을 동시에 갖는다.
- 스케줄링 단위
- 자원 할당 단위
- 성능 분석 단위
- Trace 단위

---

## 3. TileDesc 핵심 구조

### 3.1 TileDesc 정의

```text
TileDesc {
  tile_id: uint32
  tile_type: enum { COMPUTE, VECTOR, DMA, CONTROL }
  op_type: enum { GEMM, SOFTMAX, LAYERNORM, KV_LOAD, KV_STORE, ... }

  tensor_slice:
    - input_slices[]
    - output_slices[]

  dependency:
    - pred_tiles[]   # must complete before this tile
    - succ_tiles[]

  resource_hint:
    - preferred_engine: { TE | VE | DMA }
    - exclusive: bool

  latency_model:
    - est_compute_cycles
    - est_mem_cycles
    - est_sync_cycles

  runtime_state:
    - status: { WAIT, READY, RUNNING, DONE }
    - remaining_cycles
}
```

---

### 3.2 Dependency 모델

- Tile 간 의존성은 **명시적 DAG**로 표현
- 모든 dependency는 Tile ID 기준
- implicit ordering 금지

```text
Tile A ──▶ Tile B ──▶ Tile C
```

---

## 4. Tile 유형별 규약

### 4.1 Compute Tile (TE)
- GEMM, Conv, Attention MatMul
- 높은 compute density
- DMA Tile과 병렬 실행 가능

### 4.2 Vector Tile (VE)
- Softmax, LayerNorm, GELU
- Memory-bound 성향
- Compute Tile과 pipeline 가능

### 4.3 DMA Tile
- KV-cache load/store
- DRAM ↔ SPM 이동
- Compute Tile의 input producer

---

## 5. IR → Simulator Interface

Tile IR은 다음 인터페이스를 통해 시뮬레이터로 전달된다.

```text
emit_tiles(model_graph) -> TileDesc[]
```

Simulator는 IR의 순서를 신뢰하지 않으며,
**오직 dependency와 resource availability만을 기준으로 실행**한다.

---

## 6. Trace 및 Profiling 연계

각 Tile은 Trace에서 다음 정보를 남긴다.

- tile_id
- engine_type
- start_cycle / end_cycle
- stall_reason (if any)

이를 통해 **Critical Path 분석**이 가능하다.

---

## 7. 향후 확장

- Tile Fusion / Tile Split
- Dynamic latency feedback
- Tile-first ISA lowering

본 Tile IR은 정적 스케줄링 기반 모바일/엣지 NPU 시뮬레이터의 기준 IR로 설계되었다.

