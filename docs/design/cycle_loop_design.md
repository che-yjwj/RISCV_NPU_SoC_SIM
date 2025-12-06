# Cycle Loop Design
**Path:** `docs/design/cycle_loop_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-04

---

## 1. 목적
Global cycle loop는 시뮬레이터의 “메인 루프”로, **모든 엔진/메모리/ControlFSM를 한 cycle 단위로 업데이트**한다.  
이 문서는 cycle loop의 책임, 호출 순서, 종료 조건을 정의한다.

관련 스펙:
- `docs/overview/system_architecture.md`
- `docs/spec/isa/cmdq_overview.md`
- `docs/spec/timing/*.md`
- `docs/spec/trace/trace_format_spec.md`

## 2. 책임
- **입력**
  - 초기화된 SimulatorCore(엔진, ControlFSM, MemoryModel, TraceEngine 포함).
  - CMDQ와 config.
- **출력**
  - 전체 run에 대한 trace/summary.
  - optional: cycle 수, 최대 동시 DMA/TE/VE 개수 등 메타데이터.
- **주요 역할**
  - cycle 증가, per-cycle 엔진 업데이트, ControlFSM issue 호출, TraceEngine flush.
  - safety guard(최대 cycle 제한, early stop 조건) 적용.
- **하지 말아야 할 일**
  - 각 엔진의 내부 타이밍 공식 변경.
  - CMDQ 의미(ISA) 변경.

## 3. 내부 구조

### 3.1 CycleLoop 모듈
- `current_cycle: int`
- `max_cycles: Optional[int]`
- `sim_core: SimulatorCore` (ControlFSM, engines, memory, trace를 포함)

### 3.2 호출 순서
한 global cycle 내에서는 **멀티클럭 tick → 이벤트 수집 → ControlFSM issue → Trace 기록** 순으로 진행한다.

1. `tickables_in_order` 리스트(예: CPU→DMA→TE→VE→Memory→Trace)의 각 모듈에 대해 `tick(sim_cycle)` 호출.
   - 각 모듈은 `period/local_phase` 기반으로 실제 로컬 한 사이클을 실행할지 결정한다.
2. 엔진 completion 이벤트 수집.
3. ControlFSM에 이벤트 전달 + issue 시도.
4. TraceEngine에 이번 cycle의 이벤트/샘플 기록.

```pseudo
cycle = 0
while not control_fsm.is_finished() and cycle < max_cycles:
    # 1) Multi-clock tick
    for tickable in tickables_in_order:
        tickable.tick(cycle)

    # 2) 엔진 완료 이벤트 수집
    events = collect_engine_completion_events()

    # 3) ControlFSM 업데이트 및 issue
    control_fsm.consume_engine_events(events)
    issue_reqs = control_fsm.step_issue(cycle)
    for req in issue_reqs:
        engines[req.engine_type][req.engine_id].enqueue(req.cmdq_entry)

    # 4) Trace 업데이트
    trace_engine.step(cycle)

    cycle += 1
```

## 4. 알고리즘 / 플로우

### 4.1 초기화
- `cycle = 0`으로 시작.
- TraceEngine에 run_metadata/config_snapshot 기록.

### 4.2 종료 조건
- `ControlFSM.is_finished() == True` 이거나
- `cycle >= max_cycles` (오류/무한루프 방지) 인 경우 루프 종료.
- max_cycles 초과 시 trace summary에 “aborted” 플래그 기록.

### 4.3 멀티 클럭/서브사이클 규칙

각 컴포넌트는 고유한 실제 클럭을 갖지만, 시뮬레이터는 **global cycle**을 최소 공배수 단위로 잡는다.

```text
cpu_hz   = 1 GHz   (period = 1 ns)
npu_hz   = 2 GHz   (period = 0.5 ns)
dram_hz  = 0.5 GHz (period = 2 ns)

global_cycle = lcm(1, 0.5, 2) = 0.5 ns
```

global_cycle을 기준으로 각 모듈은 자신에게 할당된 `period`만큼 local phase를 누적한 뒤 `_tick_local()`을 실행한다.

### 4.4 Tickable 추상화

멀티클럭을 일반화하기 위해 모든 컴포넌트가 `Tickable` 인터페이스를 구현한다.

```python
class Tickable:
    def __init__(self, period: int = 1):
        self.period = max(1, period)
        self._phase = 0

    def tick(self, sim_cycle: int):
        self._phase += 1
        if self._phase < self.period:
            return
        self._phase = 0
        self._tick_local(sim_cycle)
```

- `period`: global cycle 대비 로컬 cycle 비율(정수).  
  예: DRAM period=4 → 4 global cycle마다 한 번 `_tick_local`.
- `_tick_local`: 실제 엔진/메모리 업데이트 수행.

대표 모듈별 기본 period는 다음과 같다.

| 모듈 | 기본 period | 설정 위치 |
| --- | --- | --- |
| ControlFSM / Host CPU | `cpu_period` (예: 2) | simulator config |
| DMAEngine Cluster | 1 | bus와 동일한 global cycle |
| TensorEngine / VectorEngine | 1 | 필요 시 latency로 세부 속도 조절 |
| Memory/Bus/NoC Model | `mem_period` (예: 2) | DRAM 속도 차이를 반영 |
| TraceEngine | 1 또는 4 | summary 모드에서는 덜 빈번 |

### 4.5 Multi-clock 스케줄 예시

```pseudo
tickables_in_order = [
    cpu_control_fsm(period=2),
    dma_cluster(period=1),
    tensor_cluster(period=1),
    vector_cluster(period=1),
    memory_model(period=2),
    trace_engine(period=4)
]

for cycle in range(max_cycles):
    for tickable in tickables_in_order:
        tickable.tick(cycle)
```

이 구조를 통해 CPU/DRAM이 느리고 DMA/TE/VE가 빠른 환경에서도 하나의 CycleLoop에서 일관성 있게 모델링할 수 있다.

### 4.6 성능/정확도 모드
- **정확도 우선 모드:** 모든 엔진/메모리 이벤트를 상세 기록.
- **속도 우선 모드:** bandwidth_samples/summary_metrics만 기록, 세부 timeline 생략.

## 5. 인터페이스
- `CycleLoop.run(sim_core: SimulatorCore, max_cycles: Optional[int]) -> TraceResult`
- `CycleLoop.step() -> None` (인터랙티브/디버깅용).
- 설정 파라미터:
  - `max_cycles`
  - trace level (full / summary / off)

## 6. 예시 시나리오
- 단일 run:
  - `sim_core = SimulatorCore.from_cmdq("cmdq.json", config)`
  - `result = CycleLoop.run(sim_core, max_cycles=10_000_000)`
  - `result.trace_path`와 summary metrics를 분석.

## 7. 향후 확장
- multi-threaded / multi-process 엔진 업데이트(큰 워크로드에서 성능 향상).
- 시뮬레이션 중단/재개 체크포인트 기능.
- 실시간 시각화를 위한 hook (cycle별 요약을 소켓/파이프에 전송).
