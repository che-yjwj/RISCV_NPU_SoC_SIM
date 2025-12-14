# Tile-level Scheduler Design (Latency-aware)

## 1. 문서 목적
본 문서는 TileRT 개념을 기반으로 한 **Tile-level Scheduler의 설계 명세**를 정의한다. 본 스케줄러는 cycle-based 전역 루프를 사용하는 NPU 시뮬레이터에서 **지연(latency) 최소화**를 목표로 한다.

---

## 2. 스케줄링 목표

### 2.1 최적화 대상

```text
Objective:
  minimize(Time_to_First_Token + Tail_Latency)
```

Throughput(tokens/sec)는 부차적 목표로 간주한다.

---

## 3. Scheduler 입력 / 출력

### 3.1 입력
- TileDesc DAG
- HW Resource 상태 (TE / VE / DMA)
- Global Cycle Counter

### 3.2 출력
- Tile Dispatch Event
- Tile Retire Event

---

## 4. 내부 데이터 구조

### 4.1 Ready Queue

```text
ReadyQueue:
  - tiles with unresolved_dependency == 0
```

### 4.2 Running Table

```text
RunningTiles:
  tile_id -> { engine, remaining_cycles }
```

### 4.3 Dependency Counter

```text
dep_count[tile_id]
```

---

## 5. Global Cycle Loop 동작

```text
for cycle in global_cycles:
  1. Update running tiles
  2. Retire completed tiles
  3. Update dependency counters
  4. Push newly-ready tiles into ReadyQueue
  5. Dispatch tiles if resources available
```

---

## 6. Dispatch 정책

### 6.1 기본 규칙
- Engine 당 1 Tile (정적 스케줄링 기준)
- DMA / Compute 병렬 허용

### 6.2 Priority 정책

Tile 우선순위는 다음 기준으로 계산한다.

```text
priority(tile) =
  critical_path_weight
  + dependency_depth_weight
  + tile_latency_weight
```

Critical Path 상 Tile이 항상 우선된다.

---

## 7. Stall 모델링

Tile이 dispatch되지 못하는 이유:
- Resource busy
- Memory contention
- Explicit barrier

Stall 원인은 Trace에 기록된다.

---

## 8. Prefill / Decode 통합 처리

Scheduler는 Prefill/Decode를 구분하지 않는다.

차이는 오직 DAG의 형태로만 나타난다.

| 항목 | Prefill | Decode |
|---|---|---|
| DAG Width | 넓음 | 좁음 |
| DAG Depth | 얕음 | 깊음 |

---

## 9. Gantt / Trace 연계

Scheduler는 다음 시각화를 지원한다.

- Tile-level Gantt Chart
- Engine Utilization Timeline
- Critical Path Highlight

---

## 10. 향후 확장

- Multi-tile per engine
- Dynamic priority feedback
- Chaos / stochastic scheduling

본 Scheduler는 **정적 스케줄링 기반 모바일 NPU 시뮬레이터**를 1차 타겟으로 한다.

