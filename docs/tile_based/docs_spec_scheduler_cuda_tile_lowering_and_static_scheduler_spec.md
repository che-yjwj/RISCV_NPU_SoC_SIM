# Tile Lowering & Static Scheduler Spec

본 문서는 **Tile-centric NPU Simulator**에서
`NPU Tile IR → HW 실행 단위(TE/VE/DMA)`로 변환하는 **Tile Lowering 규칙**과,
이를 기반으로 한 **Static Scheduler의 설계 원칙과 알고리즘**을 정의한다.

이 문서는 `tile_contract_spec.md`, `npu_tile_ir_spec.md`를 전제로 한다.

---

## 1. 문서의 목적과 위치

### 1.1 목적

- Tile IR을 **실행 가능한 HW 작업 단위**로 변환하는 규칙 고정
- 정적 스케줄링의 **결정 지점과 불변 규칙** 명시
- 성능 분석, 타이밍 모델, Gantt 시각화의 공통 기준 제공

> 이 문서는 “스케줄러 구현 가이드”가 아니라
> **스케줄러가 반드시 따라야 할 설계 헌법**이다.

---

### 1.2 파이프라인 내 위치

```
Tile IR (DAG)
   ↓  Tile Lowering
HW Tasks (TE / VE / DMA)
   ↓  Static Scheduler
Time-ordered Execution Plan
   ↓
Simulator / Timeline / Profiling
```

---

## 2. Tile Lowering 개요

Tile Lowering은 **의미 보존(semantic preserving)** 변환이다.

- 연산 의미는 변경되지 않는다.
- 단지 “어디서, 어떤 HW에서, 어떤 순서로” 실행될지를 구체화한다.

---

## 3. Tile → HW Task 분해 규칙

### 3.1 기본 원칙

1. 하나의 Tile IR op는 **하나 이상의 HW Task**로 분해된다.
2. HW Task는 반드시 하나의 Engine에 귀속된다.
3. Task 간 dependency는 Tile IR dependency를 보존한다.

---

### 3.2 Compute Tile Lowering

#### 3.2.1 GEMM_T Lowering (TE)

```
Tile IR:
  GEMM_T(A, B) -> C
```

Lowering 결과:

```
DMA_LOAD(A_tile)
DMA_LOAD(B_tile)
TE_EXEC(GEMM, A_tile, B_tile -> C_tile)
DMA_STORE(C_tile)
```

- TE tile shape은 Tile Contract에 의해 고정
- DMA load/store는 double-buffer 가능

---

#### 3.2.2 LNORM_T / SOFTMAX_T Lowering (VE)

```
Tile IR:
  LNORM_T(X) -> Y
```

Lowering 결과:

```
DMA_LOAD(X_tile)   (if not in SPM)
VE_EXEC(MEAN/VAR)
VE_EXEC(NORM)
VE_EXEC(SCALE_SHIFT)
DMA_STORE(Y_tile)
```

- VE는 pipeline stage별 latency 모델을 갖는다.
- 중간 결과는 SPM 또는 Global SRAM에 유지된다.

---

### 3.3 Memory Tile Lowering

```
LOAD_TILE(addr) -> T
```

Lowering:

```
DMA_LOAD(T)
```

```
STORE_TILE(T) -> addr
```

Lowering:

```
DMA_STORE(T)
```

---

## 4. HW Task 모델

### 4.1 HW Task 정의

```
HW_Task = {
  engine_type,   // TE | VE | DMA
  tile_id,
  latency_model,
  resource_req,
  dependencies
}
```

---

### 4.2 Engine 모델

| Engine | 특징 |
|---|---|
| TE | Tile atomic execution, high compute density |
| VE | Multi-stage pipeline, vector latency dominated |
| DMA | Bandwidth + contention model |

---

## 5. Static Scheduler 설계 원칙

### 5.1 Static Scheduling 채택 이유

- 모바일/엣지 NPU 특성
- 런타임 복잡도 최소화
- 재현 가능한 타이밍 분석

Scheduler는 **실행 전 전체 계획을 확정**한다.

---

### 5.2 Scheduler 입력

- Tile Dependency Graph (TDG)
- HW Task Graph
- Engine 수 (TE/VE/DMA)
- SPM capacity
- DMA bandwidth

---

## 6. Static Scheduling 알고리즘 (개념)

### 6.1 기본 단계

1. TDG Topological Sort
2. Ready Tile Queue 생성
3. Engine별 Dispatch Queue 관리
4. Resource availability 검사
5. Time advancement

---

### 6.2 Scheduling 우선순위 규칙 (예시)

1. Critical path 상 Tile
2. SPM reuse가 높은 Tile
3. DMA latency hiding 가능한 Tile

---

## 7. Resource Constraint 모델링

### 7.1 SPM Capacity Constraint

- 동시에 resident 가능한 tile 수 제한
- 초과 시 dispatch 불가

---

### 7.2 DMA Contention 모델

- DMA task 동시 실행 시 BW 분할
- Burst alignment penalty 반영

---

## 8. Output: Time-Ordered Execution Plan

Scheduler 출력은 다음을 포함한다.

```
Time | Engine | Task | Tile | State
```

이 출력은:
- Simulator 실행
- Gantt Chart 시각화
- 병목 분석
의 입력으로 사용된다.

---

## 9. Determinism 보장

- 동일 입력 IR → 동일 스케줄 결과
- 랜덤 요소 없음
- 실험 재현성 보장

---

## 10. Spec Summary

- Tile Lowering은 의미 보존 변환이다.
- Static Scheduler는 Tile 단위 계획을 사전에 확정한다.
- 모든 성능 분석은 Scheduler 결과를 기준으로 한다.

이 문서는 Tile-centric NPU Simulator의 실행 모델을 고정한다.

