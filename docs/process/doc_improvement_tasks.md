# Documentation Improvement Tasks
**Path:** `docs/process/doc_improvement_tasks.md`  
**Status:** Active  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
`documentation_review_summary.md`에서 도출된 문서 개선 항목을 장기적으로 추적하기 위한 체크리스트 문서이다.  
Spec-Driven Development 흐름상 **문서 우선 정비**가 필요하기 때문에, 아래 목록을 따라가며 단계적으로 반영한다.

## 2. 사용 지침
- 각 항목은 체크박스를 사용해 진행 상태를 표시한다. (`[ ]` → `[x]`)
- 필요하다면 `Owner`, `Status`, `Notes` 열을 업데이트하고, 관련 PR/이슈 링크를 Notes에 남긴다.
- 신규 개선 항목이 생기면 동일한 포맷을 유지해 섹션을 추가한다.
- 완료된 항목은 체크와 함께 Last Updated 날짜를 갱신한다.

## 3. Completed Tasks (우선순위별 체크리스트)

### 3.1 최우선 (공통 기반 정비, 완료)
| Task | Scope | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| [x] README 개선 | `README.md` | Completed (2025-12-02) | Core Maintainers | 구현 상태 표, 읽기 순서 테이블, 타깃 스코프 추가 |
| [x] Spec Index 태그 | `docs/README_SPEC.md` | Completed (2025-12-02) | Core Maintainers | 필수/권장/참고 태그 + 문서 의존 관계/우선순위 표 |
| [x] IR/CMDQ 핵심 스펙 보강 | `docs/spec/ir/npu_ir_spec.md`, `docs/spec/isa/cmdq_format_spec.md` | Completed (2025-12-02) | Core Maintainers | IR 노드 요약 표/버전 정책, CMDQ mini 예제 + 필드 필수/옵션/예약 표 |
| [x] Timing/Trace 예제 확장 | `docs/spec/timing/*.md`, `docs/spec/trace/*.md` | Completed (2025-12-02) | Core Maintainers | DMA/TE/VE 예시 config/시나리오, bandwidth/ENGINE_EVENT 샘플 및 필드 표 추가 |

### 3.2 중요 (설계 문서 디테일, 완료)
| Task | Scope | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| [x] 시뮬레이터 코어 & 루프 명확화 | `docs/design/npu_simulator_core_design.md`, `cycle_loop_design.md`, `control_fsm_design.md` | Completed (2025-12-02) | Core Maintainers | Global loop 의사코드 정리, multi-clock 규칙, 공정성/데드락 방지 정책 기술 |
| [x] CMDQ/Compiler 파이프라인 예제 | `docs/design/cmdq_generator_design.md`, `offline_compiler_design.md` | Completed (2025-12-02) | Core Maintainers | Golden CMDQ mini 예제, pass graph 및 IR→CMDQ 파이프라인 개념도 추가 |
| [x] 컴파일러 세부 모듈 표/예시 | `docs/design/ir_builder_design.md`, `tiling_planner_design.md`, `spm_allocator_design.md`, `static_scheduler_design.md` | Completed (2025-12-02) | Core Maintainers | ONNX 지원 op 표, 1D/2D/Attention 타일링 전략, SPM 배치 예시, 스케줄러 우선순위 pseudo-code 추가 |
| [x] 엔진/비주얼라이저 다이어그램 | `docs/design/te_engine_design.md`, `ve_engine_design.md`, `dma_engine_design.md`, `visualizer_design.md` | Completed (2025-12-02) | Core Maintainers | TE/VE 파이프라인 스케치, DMA 상태 전이, Visualizer MVP vs 확장 뷰 정리 |

### 3.3 후순위 (프로세스·테스트 매핑, 완료)
| Task | Scope | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| [x] Process 가이드 구체화 | `docs/process/spec_driven_development_workflow.md`, `contribution_and_review_guide.md`, `naming_convention.md`, `versioning_and_changelog_guide.md` | Completed (2025-12-02) | Core Maintainers | PR/Issue 규칙, 리뷰 최소 기준, 네이밍 안티 패턴, Spec↔코드 버전 매핑 정책 추가 |
| [x] 테스트 문서와 스펙 매핑 | `docs/test/test_plan.md`, `unit_test_spec.md`, `integration_test_spec.md`, `performance_validation_protocol.md`, `golden_trace_examples.md` | Completed (2025-12-02) | Core Maintainers | 대표 ID↔Spec/Design 매핑, ONNX 예제/메트릭, 허용 오차, golden trace 비교 필드 정리 |

---

## 4. 향후 관리
- 모든 항목이 완료되면 해당 섹션을 “Completed”로 이동하거나, 새로운 개선 사항이 나오면 우선순위를 재분류한다.
- 문서 개선 PR을 보낼 때 이 파일을 함께 업데이트하여 진행 상황을 명확히 공유한다.

## 5. Backlog (향후 추가 개선 아이템)
- 현재 백로그는 비어 있으며, 새로운 문서 개선 아이디어가 생기면 아래 표에 항목을 추가한다.

| Task | Scope | Priority | Notes |
| --- | --- | --- | --- |
| (예시) IR 예제 확장 | `docs/spec/ir/*.md` | Medium | 더 복잡한 LLM 블록 IR 스니펫 추가 |
| (예시) Trace 튜토리얼 추가 | `docs/spec/trace/*.md`, `docs/design/visualizer_design.md` | Low | “처음 보는 사람용” walk-through 문서 작성 |
