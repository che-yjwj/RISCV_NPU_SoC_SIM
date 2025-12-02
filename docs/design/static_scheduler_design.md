# Static Scheduler Design
**Path:** `docs/design/static_scheduler_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
StaticScheduler는 TileGraph + SPM allocation + 엔진 구성 정보를 기반으로 **정적 tile-level 실행 순서와 deps를 생성**한다.  
결과는 CMDQGenerator가 바로 사용할 수 있는 스케줄 DAG 형태가 된다.

관련 스펙:
- `docs/spec/isa/cmdq_overview.md`
- `docs/overview/dataflow_overview.md`

## 2. 책임
- **입력**
  - TileGraph (tile 노드, 데이터 의존성 edges).
  - SPM allocation 정보 (각 tile의 bank/offset).
  - 엔진 구성 (`num_te`, `num_ve`, DMA channel 수).
- **출력**
  - tile-level schedule DAG:
    - 각 tile에 할당된 엔진 (logical TE/VE/DMA 슬롯).
    - deps_before 관계 (CMDQ의 deps 필드에 바로 대응).
- **주요 역할**
  - DMA LOAD/STORE, TE tile, VE tile 간의 순서/병렬 실행 계획.
  - SPM reuse와 bank conflict를 고려하여 타일 실행 순서를 조정.
- **하지 말아야 할 일**
  - 실제 cycle-level timing 계산.
  - CMDQ JSON 생성(이는 CmdqGenerator 책임).

## 3. 내부 구조

### 3.1 ScheduleEntry
```python
class ScheduleEntry:
    id: int              # schedule-local id
    tile_id: str
    op_class: str        # DMA_LOAD, DMA_STORE, TE, VE
    engine_type: str     # DMA/TE/VE
    engine_index: int    # logical 엔진 index
    deps_before: list[int]
```

### 3.2 그래프 표현
- `ScheduleDAG`:
  - `entries: list[ScheduleEntry]`
  - `edges: deps_before 관계 (from entry.id to dependent entry.id)`

## 4. 알고리즘 / 플로우

### 4.1 기본 전략
1. TileGraph를 레이어 순서/topological order로 순회.
2. 각 tile에 대해:
   - 필요 DMA LOAD_TILE (ifm/wgt), TE/VE tile, DMA STORE_TILE을 logical 순서로 생성.
3. 데이터 의존성 기반으로 deps_before 추가:
  - LOAD → TE/VE → STORE 흐름.
  - TileGraph edges를 따라 producer tile의 STORE와 consumer tile의 LOAD/TE 사이에 deps 추가.

### 4.2 엔진 배정
- 간단한 라운드로빈 또는 load-balance heuristic:
  - TE: `te_id = next_available_te(layer_or_tile_group)`.
  - VE: `ve_id = next_available_ve(layer_or_tile_group)`.
  - DMA: 단일 또는 소수 channel에 round-robin.

### 4.3 SPM 관점 조정
- SPMAllocator에서 제공하는 lifetime 정보와 bank occupancy를 기반으로:
  - bank conflict가 커질 것으로 예상되는 타일은 순서를 조정하거나 deps를 삽입해 overlap 완화.

### 4.4 우선순위 정책 의사코드 (예시)

간단한 priority 기반 스케줄링 예시:

```pseudo
ready_queue = PriorityQueue()

for tile in tile_graph.topological_order():
    enqueue_initial_ops_for_tile(tile)  # LOAD / TE/VE / STORE

while not ready_queue.empty():
    entry = ready_queue.pop_max_priority()

    engine = select_engine(entry)
    if engine_can_accept(engine):
        assign_engine(entry, engine)
        mark_scheduled(entry)
        update_successors(entry, ready_queue)
    else:
        # 엔진이 바쁘면 우선순위를 약간 낮추고 다시 큐에 삽입
        decay_priority(entry)
        ready_queue.push(entry)
```

우선순위 예시:
- DMA LOAD 우선 → 데이터 준비를 먼저 해서 TE/VE idle을 줄인다.
- TE는 ready tile 중 SPM conflict가 적은 순서로 선택.
- VE는 Latency-critical path(예: LayerNorm, Softmax) 연산에 가중치를 줄 수 있다.

## 5. 인터페이스
- `StaticScheduler.schedule(tile_graph, spm_alloc, hw_config) -> ScheduleDAG`

구성 파라미터:
- priority 정책 (레이어 우선 vs 타일 우선).
- multi-engine balancing 정책.

## 6. 예시 시나리오
- 2개의 TE를 가진 환경에서:
  - TileGraph의 독립 타일들이 TE0/TE1에 번갈아 배정되고,  
    deps가 없는 타일은 최대한 병렬로 실행되도록 스케줄이 생성되는지 확인.

## 7. 향후 확장
- critical path 기반 우선순위 스케줄링.
- 메모리/대역폭 aware 스케줄링 (DMA latency와 TE/VE 우선순위 조정).
