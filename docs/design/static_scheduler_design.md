# Static Scheduler Design
**Path:** `docs/design/static_scheduler_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-04

---

## 1. 목적
StaticScheduler는 TileGraph + SPM allocation + 엔진 구성 정보를 기반으로 **정적 tile-level 실행 순서와 deps를 생성**한다.  
결과는 CMDQGenerator가 바로 사용할 수 있는 스케줄 DAG 형태가 된다.

관련 스펙:
- `docs/spec/ir/npu_ir_spec.md`
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
  - KV cache tile(K/V load/store) 흐름을 Prefill/Decode 단계에 맞게 포함.
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

### 4.5 LLM / KV-aware 스케줄링
- **Prefill 단계 (KV_STORE_TILE 중심)**  
  - TE/VE 타일 완료 후 `KV_STORE_TILE`을 바로 enqueue하여 KV append를 보장.  
  - 동일 head의 KV_STORE는 토큰 순서(t_start 기준)로 정렬, deps_before를 통해 순서 유지.  
  - KV STORE 이후의 activation reuse(예: 다음 블록)에는 STORE→LOAD deps를 명시.
- **Decode 단계 (KV_LOAD_TILE 중심)**  
  - 토큰당 반복 루프에서 `KV_LOAD_TILE`을 TE/VE보다 앞서 배치해 latency를 숨긴다.  
  - head별로 KV_LOAD를 묶어 병렬 DMA를 허용하되, 동일 head의 시간 구간이 겹치지 않도록 deps를 추가한다.  
  - KV_LOAD→TE_QKT_TILE/TE_AV_TILE/VE_SOFTMAX_TILE 간 deps를 명시해, 잘못된 구간이 사용되지 않게 한다.
- **채널/엔진 정책**  
  - DMA 채널이 여러 개라면 activation/load와 KV_LOAD/KV_STORE를 분리된 라운드로빈 슬롯에 배정하여 노이즈를 줄인다.  
  - `tensor_role`이 `kv`인 DMA를 별도 priority(+δ)로 두어 TE idle을 방지한다.
- **SPM/메모리 고려**  
  - KV LOAD 타일은 SPM을 짧게 점유하므로, bank conflict가 적은 bank로 우선 배치해 TE와 충돌을 줄인다.  
  - Prefill에서 KV STORE 직후 동일 bank를 재사용할 경우, STORE 완료를 deps로 명시해 over-write를 방지.

## 5. 인터페이스
- `StaticScheduler.schedule(tile_graph, spm_alloc, hw_config) -> ScheduleDAG`

구성 파라미터:
- priority 정책 (레이어 우선 vs 타일 우선).
- multi-engine balancing 정책.

## 6. 예시 시나리오
- 2개의 TE를 가진 환경에서:
  - TileGraph의 독립 타일들이 TE0/TE1에 번갈아 배정되고,  
    deps가 없는 타일은 최대한 병렬로 실행되도록 스케줄이 생성되는지 확인.
- MatMul + GELU 블록에 대해서는:
  - `docs/overview/dataflow_overview.md` 3.9 섹션과  
    `docs/spec/ir/npu_ir_spec.md`의 FFN 예제,  
    `docs/spec/isa/cmdq_format_spec.md` 15장의 CMDQ 시퀀스를 함께 참고하면  
    IR → TileGraph → ScheduleDAG → CMDQ로 이어지는 흐름을 end-to-end로 추적할 수 있다.
- LLM Prefill/Decode 시나리오:
  - Prefill: TE_GEMM_TILE/TE_AV_TILE → VE_SOFTMAX_TILE → `KV_STORE_TILE` 순서와 deps가 올바른지, head별 KV append 순서가 유지되는지 확인.
  - Decode: 토큰 step마다 `KV_LOAD_TILE`이 TE/VE 연산보다 먼저 issue되어 latency가 숨겨지는지, head별 구간이 겹치지 않는지 확인.

## 7. 향후 확장
- critical path 기반 우선순위 스케줄링.
- 메모리/대역폭 aware 스케줄링 (DMA latency와 TE/VE 우선순위 조정).
