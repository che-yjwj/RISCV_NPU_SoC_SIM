# Cycle Loop Design
**Path:** `docs/design/cycle_loop_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

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
cycle = 0
while not control_fsm.is_finished() and cycle < max_cycles:
    # 1) 엔진/메모리 업데이트
    dma_engines.step_all(cycle, memory_model, trace_engine)
    tensor_engines.step_all(cycle, memory_model, trace_engine)
    vector_engines.step_all(cycle, memory_model, trace_engine)
    memory_model.step(cycle, trace_engine)

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

### 4.3 멀티 클럭/서브사이클 규칙 (옵션)

초기 버전에서는 모든 서브시스템(DRAM/NPU/CPU)이 동일 cycle 도메인에 있는 것으로 가정한다.  
멀티 클럭을 도입할 때는 다음과 같은 N:1 규칙을 사용한다.

```text
cpu_hz   = 1 GHz
npu_hz   = 2 GHz
dram_hz  = 0.5 GHz

global_cycle = lcm(1/cpu_hz, 1/npu_hz, 1/dram_hz) 기준
→ 예: global_cycle = 0.5 ns
```

```pseudo
for cycle in range(max_cycles):
    if cycle % 2 == 0:      # 1ns마다 CPU step
        cpu.step(cycle)
    if cycle % 1 == 0:      # 매 cycle NPU step
        npu.step(cycle)
    if cycle % 4 == 0:      # 2ns마다 DRAM step
        dram.step(cycle)
```

이 규칙을 사용하면 서로 다른 클럭 도메인을 단일 global cycle loop로 통합할 수 있다.  
실제 비율과 서브사이클 세분화는 timing spec/config에 따라 결정한다.

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
