# Codex Vibe Coding & SDD Workflow Guide
Status: Draft v1  
Owner: TBD  
Last Updated: 2025-12-02  

---

## 1. 목적 (Purpose)

본 문서는 `RISCV_NPU_SoC_SIM` 레포지토리에서  
**Codex 기반 Vibe Coding**을 사용할 때도  
이미 존재하는 **Spec/Design/Test 문서 구조**와 **Milestone Plan**을 따르는 개발 방식을 정의한다.

특히 다음 두 요소를 연결하는 것이 목표이다.

- 마일스톤 플랜: `docs/process/milestone_plan.md`
- SDD 프로세스: `docs/process/spec_driven_development_workflow.md`

Codex는 설계를 대신하는 도구가 아니라,  
“문서로 정의된 설계를 빠르게 구현하는 도우미”로 사용한다.

---

## 2. 기본 철학

### 2.1 문서 우선 (Spec → Design → Code → Test)

- 개발 순서는 항상 문서가 먼저다.
  - Spec: `docs/spec/**`
  - Design: `docs/design/**`
  - Process: `docs/process/**`
  - Test Plan: `docs/test/**`
- Codex에 구현을 요청하기 전에:
  1. 어떤 Phase/Task를 수행할지 선택하고
  2. 관련 Spec/Design 문서 섹션을 확인한 뒤
  3. 그 내용을 프롬프트에 포함한다.

### 2.2 Codex는 구현 가속기, 설계자는 사람이거나 문서

- 클래스 구조, 모듈 분리, 책임 분할은  
  `docs/design/*.md`, `docs/overview/*.md` 에서 정의한다.
- Codex는 다음에 집중한다.
  - 데이터 클래스/타입 정의
  - 이미 정의된 인터페이스의 구현
  - 반복적인 boilerplate 생성
  - 테스트 코드/샘플 생성

### 2.3 코드 ↔ 문서 트레이서빌리티 확보

- 각 주요 클래스/함수는 어떤 문서/섹션에서 왔는지 연결 관계를 남긴다.

예시:

```python
# Spec: docs/spec/ir/npu_ir_spec.md §2.1
# Design: docs/design/ir_builder_design.md §3
class IrBuilderPass:
    ...
```

---

## 3. Milestone Plan과 Codex 사용 흐름

### 3.1 단일 Source of Truth: `milestone_plan.md`

- 모든 Phase/Task/Done Criteria는 `docs/process/milestone_plan.md`에 정의한다.
- Codex 세션을 시작할 때는 항상 다음을 명시한다.
  1. 현재 작업 중인 Phase (예: Phase 1)
  2. 선택한 Task (예: IrBuilderPass 최소 구현)
  3. 관련 Spec/Design 문서 목록

예시:

- Phase: 1 (MatMul-only E2E)
- Task: `IrBuilderPass: ONNX MatMul → IR 변환`
- Spec/Design:
  - `docs/spec/ir/npu_ir_spec.md`
  - `docs/design/ir_builder_design.md`

### 3.2 Phase → Task → Codex 호출 절차

1. Phase 선택
2. Milestone Plan에서 Task 하나 선택
3. 관련 Spec/Design 문서에서 필요한 내용 발췌
4. Codex 프롬프트 작성 (4장 템플릿 참조)
5. Codex 결과 검토 및 수정
6. 해당 Task에 대응하는 테스트 작성/실행
7. Task 체크 및 커밋

---

## 4. Codex 프롬프트 템플릿

아래 템플릿은 GitHub Codespaces, VS Code Codex 확장 등에서 사용할 수 있는 기본 형태다.  
중요한 점은 “Phase/Task/Spec/Design 문맥을 항상 상단에 포함하는 것”이다.

### 4.1 도메인 타입/데이터 클래스 구현

상황: Phase 0에서 IR/Tensor/CMDQ/Trace 타입 정의.

```text
Context:
- Project: RISCV_NPU_SoC_SIM
- Phase: 0 (skeleton)
- Task: Define core domain dataclasses for IR, Tensor, Quantization, CMDQ, Timing, Trace.

Relevant specs:
- docs/spec/ir/npu_ir_spec.md
- docs/spec/ir/tensor_metadata_spec.md
- docs/spec/ir/quantization_ir_extension.md
- docs/spec/isa/cmdq_format_spec.md
- docs/spec/trace/trace_format_spec.md

Goal:
- Implement Python dataclasses in riscv_npu_sim/compiler/ir/core_types.py.
- Focus on structure and type hints only, no business logic.

Requirements:
- Use @dataclass.
- Class names: TensorMeta, QuantMeta, IrNode, IrGraph, CmdqEntry, TimingProfile, TraceEvent.
- Field names and types must follow the specs.
- Do not implement complex methods; only simple helpers if necessary.

Please output only Python code.
```

### 4.2 Compiler Pass 스켈레톤

상황: Phase 1에서 TilingPlannerPass 스켈레톤.

```text
Context:
- Project: RISCV_NPU_SoC_SIM
- Phase: 1 (MatMul-only E2E)
- Task: Implement minimal TilingPlannerPass skeleton.

Relevant design:
- docs/design/tiling_planner_design.md

Goal:
- Implement class TilingPlannerPass in riscv_npu_sim/compiler/passes/tiling_planner.py.

Requirements:
- For Phase 1, assume no real tiling:
  - Treat the whole MatMul as a single tile.
- Follow the design structure: class name, method signatures (run or plan), inputs/outputs.
- Insert TODO comments where Phase 2/3 will extend tiling policies.
- Do not add features not mentioned in the spec/design.

Please output only Python code.
```

### 4.3 Simulator Engine 구현

상황: Phase 2에서 TeEngine 타이밍 모델 구현.

```text
Context:
- Project: RISCV_NPU_SoC_SIM
- Phase: 2 (Timing/Engine realization)
- Task: Implement TeEngine with timing model.

Relevant specs and design:
- docs/spec/timing/te_timing_spec.md
- docs/design/te_engine_design.md
- docs/design/npu_simulator_core_design.md

Goal:
- Implement class TeEngine in riscv_npu_sim/simulator/engines/te_engine.py.

Requirements:
- Implement Engine interface:
  - can_accept(cmd: CmdqEntry) -> bool
  - issue(cmd: CmdqEntry, cycle: int) -> None
  - step(cycle: int) -> None
- Use TimingProfile.te_mac_per_cycle to estimate latency:
  - finish_cycle = cycle + ceil(macs / te_mac_per_cycle)
- Record start/end events to TraceCollector according to trace_format_spec.md.
- Make sure naming and behavior follow the design docs.

Please output only Python code.
```

---

## 5. Task ID와 경량 자동화 아이디어

### 5.1 Task ID 도입

`docs/process/milestone_plan.md`의 Task 항목에 ID를 부여할 수 있다.

예시:

```markdown
- [ ] (P0-IR-CORE-001) Define core IR/Tensor/CMDQ dataclasses
- [ ] (P1-C-IRB-001) IrBuilderPass: ONNX MatMul → IR
- [ ] (P1-C-TLP-001) TilingPlannerPass: single-tile MatMul
- [ ] (P1-S-TE-001) TeEngine: minimal latency model
```

활용:

- 커밋 메시지: `feat: implement TeEngine skeleton (P1-S-TE-001)`
- PR 제목: `[P1-S-TE-001] Implement TeEngine skeleton`
- 테스트 파일명: `test_te_engine_p1_s_te_001.py` 등

### 5.2 Task CLI 스크립트 (선택적)

`tools/doc_status.py`와 유사하게,  
`tools/task_cli.py`를 만들어 Milestone Plan과 연계할 수 있다.

예상 기능:

- `python tools/task_cli.py list --phase 1`
- `python tools/task_cli.py next`
- `python tools/task_cli.py show P1-C-IRB-001`

이 스크립트는 다음을 출력할 수 있다.

- Task ID, 설명, Phase
- 관련 Spec/Design 문서 경로
- Codex 프롬프트 템플릿 초안

Codex Vibe Coding 시에는  
`task_cli.py` 출력 내용을 그대로 프롬프트 상단에 붙여넣고,  
그 아래에 세부 요구사항만 추가하면 된다.

---

## 6. 실제 Vibe Coding 세션 예시

1. 오늘 Phase 선택  
   - 예: Phase 1

2. Milestone Plan에서 Task 선택  
   - `(P1-C-IRB-001) IrBuilderPass: ONNX MatMul → IR`

3. 관련 Spec/Design 열기  
   - `docs/spec/ir/npu_ir_spec.md`  
   - `docs/design/ir_builder_design.md`

4. Codex 프롬프트 생성  
   - 4장 템플릿에 Task/Spec/Design 정보를 채워 넣음

5. Codex의 코드 결과 검토  
   - 문서와 비교하여 구조/타입/이름이 일치하는지 확인
   - 어긋나면 수동 수정 또는 프롬프트 보정 후 재요청

6. 테스트 작성 및 실행  
   - `tests/unit/test_ir_builder_matmul.py` 추가
   - `pytest` 실행

7. Task 완료 처리  
   - `milestone_plan.md` 체크박스 업데이트
   - 커밋/PR에 Task ID 포함

---

## 7. 결론

Codex 기반 Vibe Coding을 사용할 때에도,  
문서 리뷰와 개선 작업의 단일 흐름은 다음 세 문서를 중심으로 유지한다.

- 리뷰 스냅샷: `docs/process/archive/review_by_chatgpt_v1.md`, `docs/process/archive/review_by_chatgpt_v2.md`  
- 요약 및 기준선: `docs/process/documentation_review_summary.md`  
- 실행 가능한 체크리스트: `docs/process/doc_improvement_tasks.md`

실제 작업 순서는 다음 패턴을 따른다.

1. 리뷰 스냅샷(v1/v2)을 참고해 개선 방향을 이해한다.  
2. `documentation_review_summary.md`에서 해당 영역의 요약/권장사항을 확인한다.  
3. `doc_improvement_tasks.md`에서 관련 Task를 선택하거나 신규 항목을 추가한다.  
4. 선택한 Task와 연결된 Spec/Design/Test 문서들을 Codex 프롬프트에 포함해 구현/수정을 진행한다.  
5. 작업이 끝나면 Task 상태를 업데이트하고, 필요 시 summary나 review_v* 문서를 갱신한다.

이 흐름을 따르면, Codex는 어디까지나  
“문서에서 정의된 설계를 빠르게 구현하고 검증하는 도우미”로 남고,  
문서 구조와 아키텍처 의사결정은 항상 사람이 주도하게 된다.

이 가이드는 다음을 보장한다.

- Codex를 사용하면서도 SDD의 원칙(문서 우선, Spec/Design 중심)을 잃지 않는다.
- Milestone Plan과 Phase/Task 구조를 기반으로,  
  Codex가 “설계를 망가뜨리지 않고 코드를 채워 넣는 도구”로 동작하게 한다.
- Task ID, 프롬프트 템플릿, 경량 CLI를 활용하여  
  Vibe Coding 세션을 반복 가능하고 추적 가능한 개발 루프로 만든다.

이 문서는 `docs/process/vibe_coding_sdd_guide.md`로 추가하는 것을 권장하며,  
실제 사용 경험에 따라 템플릿과 절차를 계속 보완해 나간다.
