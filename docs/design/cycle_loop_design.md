# Cycle Loop Design
**Path:** `docs/design/cycle_loop_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
Global cycle loop는 시뮬레이터의 “메인 루프”로, **모든 엔진/메모리/ControlFSM를 한 cycle 단위로 업데이트**한다.  
이 문서는 cycle loop의 책임, 호출 순서, 종료 조건을 정의한다.

관련 스펙:
- `docs/overview/system_architecture.md`
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
한 cycle 내에서 호출 순서 예:
1. DMA/TE/VE/MemoryModel step (상태/latency 진전).
2. 엔진 completion 이벤트 수집.
3. ControlFSM에 이벤트 전달 + issue 시도.
4. TraceEngine에 이번 cycle의 이벤트/샘플 기록.

```pseudo
while not control_fsm.is_finished() and cycle < max_cycles:
    engines.step_all(cycle, memory_model, trace_engine)
    events = engines.collect_completion_events()
    control_fsm.consume_engine_events(events)
    control_fsm.step_issue(cycle)
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

### 4.3 성능/정확도 모드
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
