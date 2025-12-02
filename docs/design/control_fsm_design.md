# Control FSM Design
**Path:** `docs/design/control_fsm_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
Control FSM은 CMDQ를 순차적으로 해석하고, **deps와 엔진 상태를 고려해 issue 가능한 명령을 선택**하는 상태 머신이다.  
이 문서는 Control FSM의 책임, 내부 상태, issue 알고리즘을 정의한다.

관련 스펙:
- `docs/spec/isa/cmdq_overview.md`
- `docs/spec/isa/cmdq_format_spec.md`

## 2. 책임
- **입력**
  - CMDQ 엔트리 배열 (`opcode`, `deps_before`, `deps_after`, `layer_id` 등).
  - 엔진 상태 (DMA/TE/VE의 busy/free, 큐 여유).
  - 엔진 completion 이벤트(어떤 CMDQ id가 언제 끝났는지).
- **출력**
  - “issue 요청”: 특정 CMDQ 엔트리를 특정 엔진 큐에 enqueue.
  - 시뮬레이터 코어에 전달할 상태 플래그 (`finished`, `stalled` 등).
- **주요 역할**
  - deps_before가 모두 만족된 엔트리 중에서 issue 가능한 엔트리를 찾는다.
  - 동일 cycle에 여러 엔트리를 issue할 수 있지만, 각 엔진의 큐/리소스 제약을 준수.
- **하지 말아야 할 일**
  - 타이밍 계산(DMA/TE/VE 내부 latency는 엔진이 담당).
  - CMDQ 포맷/의미 변경 (스펙에서 정의).

## 3. 내부 구조

### 3.1 상태 표현
- `EntryState`: `NOT_ISSUED`, `READY`, `ISSUED`, `COMPLETED`.
- `cmdq_state[id]`:
  - `deps_remaining`: 아직 완료되지 않은 deps_before 개수.
  - `state`: 위 상태 중 하나.
- `ready_queues`:
  - 엔진 타입별 ready 리스트 (예: DMA_ready, TE_ready, VE_ready).

### 3.2 상태 머신 개요
```text
IDLE → SCAN_CMDQ → UPDATE_READY_SET → ISSUE_TO_ENGINES → (IDLE 또는 DONE)
```
- DONE: `END` 엔트리가 COMPLETED 상태가 되면 전환.

## 4. 알고리즘 / 플로우

### 4.1 deps 갱신
엔진에서 completion 이벤트가 들어오면:
1. `completed_id`에 대해 `cmdq_state[completed_id].state = COMPLETED`.
2. 모든 엔트리를 순회하거나, reverse deps graph를 사용해  
   해당 id를 deps_before에 포함하던 엔트리의 `deps_remaining`을 1 감소.
3. `deps_remaining == 0`이고 아직 `NOT_ISSUED`이면 `READY`로 전환.

### 4.2 issue 규칙 (baseline 정책)
```pseudo
function step_issue(cycle):
    issued = []

    # 1) CMDQ 순서를 유지하면서 READY 엔트리 스캔
    for entry in cmdq:
        if entry.state != READY:
            continue

        target_engine = select_engine_for(entry)
        if not engine_can_accept(target_engine):
            continue

        issue_to_engine(entry.id, target_engine)
        entry.state = ISSUED
        issued.append(entry.id)

    return issued
```

- `select_engine_for`는 `opcode`와 필드(`te_id`, `ve_id`)에 따라 엔진을 선택.
- baseline에서는 단순 “CMDQ 순서 + 엔진 큐 여유 여부”를 사용한다.

### 4.3 데드락/라이브락 방지 및 공정성 정책 (확장)

멀티 DMA/TE/VE 환경에서는 starvation-free 스케줄링이 필요하다.  
간단한 공정성(fairness) 정책 예시는 다음과 같다.

```pseudo
for engine_type in ["DMA", "TE", "VE"]:
    # 라운드 로빈 방식으로 ready_queues를 순회
    queue = ready_queues[engine_type]
    start_idx = rr_cursor[engine_type]

    for i in range(len(queue)):
        idx = (start_idx + i) % len(queue)
        entry_id = queue[idx]
        entry = cmdq[entry_id]

        if not engine_can_accept(engine_type, entry):
            continue

        issue_to_engine(entry_id, engine_type)
        entry.state = ISSUED
        rr_cursor[engine_type] = (idx + 1) % len(queue)
        break
```

정책 요약:
- 엔진 타입별 round-robin cursor(`rr_cursor`)를 유지해 특정 엔트리가 무한정 밀리지 않도록 한다.
- 일정 cycle 동안 READY였지만 issue되지 못한 엔트리에 대해 “age 기반 가중치”를 둘 수도 있다.

### 4.3 종료 조건
- `opcode == END`인 엔트리가 `COMPLETED`가 된 경우:
  - `finished = True`.

## 5. 인터페이스 (예시)
- `ControlFSM.__init__(cmdq, engine_registry)`
- `ControlFSM.consume_engine_events(events: list[EngineEvent])`
- `ControlFSM.step_issue(cycle: int) -> list[IssueRequest]`
- `ControlFSM.is_finished() -> bool`

`IssueRequest` 예:
```python
IssueRequest(
    cmdq_id=42,
    engine_type="TE",
    engine_id=0,
)
```

## 6. 예시 시나리오
- CMDQ:
  - 0: DMA_LOAD_TILE(ifm), 1: DMA_LOAD_TILE(wgt), 2: TE_GEMM_TILE, 3: END
- deps:
  - 2.deps_before = [0, 1]
  - 3.deps_before = [2]
- 플로우:
  1. cycle 0: 0,1은 READY → DMA 엔진으로 issue.
  2. DMA 완료 이벤트 수신 후 2.deps_remaining=0 → READY.
  3. TE 엔진이 free일 때 2 issue.
  4. TE 완료 이벤트 후 3 READY → ControlFSM가 `END` issue 및 완료 확인 → finished.

위 시나리오에서 공정성 정책이 추가된 경우에도:
- 0,1은 동일 타입(DMA) ready 큐에서 round-robin으로 선택되어 issue.
- 2는 deps가 모두 만족된 시점 이후 가장 먼저 issue 가능한 TE 엔트리로 처리된다.

## 7. 향후 확장
- issue 정책 개선:
  - 엔진별 load balancing, deadline 기반 우선순위, LLM 토큰/레이어 aware 스케줄링.
- multi-CMDQ 지원:
  - 여러 CMDQ를 하나의 FSM이 관리하거나, FSM 여러 개를 계층적으로 구성.
- 디버그/시각화:
  - issue/complete 이벤트를 별도 trace 스트림으로 기록하여 스케줄링 품질 분석.
