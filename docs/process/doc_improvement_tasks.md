# Documentation Improvement Tasks
**Path:** `docs/process/doc_improvement_tasks.md`  
**Status:** Active  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-03

---

## 1. 목적
`documentation_review_summary.md`에서 도출된 문서 개선 항목을 장기적으로 추적하기 위한 체크리스트 문서이다.  
Spec-Driven Development 흐름상 **문서 우선 정비**가 필요하기 때문에, 아래 목록을 따라가며 단계적으로 반영한다.

## 2. 사용 지침
- 모든 Task는 아래 단일 목록에서 관리한다.
- 각 Task 앞의 체크박스(`[ ]` → `[x]`)로 완료 여부를 표시한다.
- `Priority`, `Status`, `Notes` 열은 필요에 따라 갱신하고, 관련 PR/이슈 링크를 Notes에 남긴다.
- 신규 개선 항목이 생기면 동일한 포맷으로 표에 한 줄을 추가한다.

---

## 3. Task 목록

| Task | Scope | Priority | Status | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| [x] README 개선 | `README.md` | High | Completed (2025-12-02) | Core Maintainers | 구현 상태 표, 읽기 순서 테이블, 타깃 스코프 추가 |
| [x] Spec Index 태그 | `docs/README_SPEC.md` | High | Completed (2025-12-02) | Core Maintainers | 필수/권장/참고 태그 + 문서 의존 관계/우선순위 표 |
| [x] IR/CMDQ 핵심 스펙 보강 | `docs/spec/ir/npu_ir_spec.md`, `docs/spec/isa/cmdq_format_spec.md` | High | Completed (2025-12-02) | Core Maintainers | IR 노드 요약 표/버전 정책, CMDQ mini 예제 + 필드 필수/옵션/예약 표 |
| [x] Timing/Trace 예제 확장 | `docs/spec/timing/*.md`, `docs/spec/trace/*.md` | Medium | Completed (2025-12-02) | Core Maintainers | DMA/TE/VE 예시 config/시나리오, bandwidth/ENGINE_EVENT 샘플 및 필드 표 추가 |
| [x] 시뮬레이터 코어 & 루프 명확화 | `docs/design/npu_simulator_core_design.md`, `cycle_loop_design.md`, `control_fsm_design.md` | Medium | Completed (2025-12-02) | Core Maintainers | Global loop 의사코드 정리, multi-clock 규칙, 공정성/데드락 방지 정책 기술 |
| [x] CMDQ/Compiler 파이프라인 예제 | `docs/design/cmdq_generator_design.md`, `offline_compiler_design.md` | Medium | Completed (2025-12-02) | Core Maintainers | Golden CMDQ mini 예제, pass graph 및 IR→CMDQ 파이프라인 개념도 추가 |
| [x] 컴파일러 세부 모듈 표/예시 | `docs/design/ir_builder_design.md`, `tiling_planner_design.md`, `spm_allocator_design.md`, `static_scheduler_design.md` | Medium | Completed (2025-12-02) | Core Maintainers | ONNX 지원 op 표, 1D/2D/Attention 타일링 전략, SPM 배치 예시, 스케줄러 우선순위 pseudo-code 추가 |
| [x] 엔진/비주얼라이저 다이어그램 | `docs/design/te_engine_design.md`, `ve_engine_design.md`, `dma_engine_design.md`, `visualizer_design.md` | Low | Completed (2025-12-02) | Core Maintainers | TE/VE 파이프라인 스케치, DMA 상태 전이, Visualizer MVP vs 확장 뷰 정리 |
| [x] Process 가이드 구체화 | `docs/process/spec_driven_development_workflow.md`, `contribution_and_review_guide.md`, `naming_convention.md`, `versioning_and_changelog_guide.md` | Medium | Completed (2025-12-02) | Core Maintainers | PR/Issue 규칙, 리뷰 최소 기준, 네이밍 안티 패턴, Spec↔코드 버전 매핑 정책 추가 |
| [x] 테스트 문서와 스펙 매핑 | `docs/test/test_plan.md`, `unit_test_spec.md`, `integration_test_spec.md`, `performance_validation_protocol.md`, `golden_trace_examples.md` | Medium | Completed (2025-12-02) | Core Maintainers | 대표 ID↔Spec/Design 매핑, ONNX 예제/메트릭, 허용 오차, golden trace 비교 필드 정리 |
| [x] Overview 계층 강화 | `README.md`, `docs/README_SPEC.md`, `docs/overview/*.md` | High | Completed (2025-12-03) | Core Maintainers | v2 리뷰 기준: Documentation Reading Guide, onnx→ir→compile→sim 파이프라인 다이어그램, SoC 관점 블록 다이어그램 및 end-to-end 예제 추가. README_SPEC Reading Guide 및 overview 문서 간 상호 참조를 보강하고, one-page overview 문서들(system_architecture_overview/compute_dataflow_overview/memory_noc_overview)에 SoC/LLM/메모리 관점 설명을 추가함 |
| [x] 신규/보완 Overview 문서 설계 | `docs/overview/system_architecture_overview.md`, `compute_dataflow_overview.md`, `memory_noc_overview.md`, `sdd_devflow_overview.md` | Medium | Completed (2025-12-03) | Core Maintainers | 기존 overview 문서와 역할을 조정하여, system/dataflow/memory+NoC/devflow를 각각 한 페이지에서 설명. 네 개 문서의 스켈레톤(목적/대상 독자/관련 문서/간단 다이어그램)을 추가하고, system/compute/memory/devflow 개요 내용을 채워넣어 “개론 페이지” 수준까지 보강함 |
| [x] IR/ISA/CMDQ 파이프라인 정렬 | `docs/spec/ir/*.md`, `docs/spec/isa/*.md`, `docs/design/static_scheduler_design.md`, `cmdq_generator_design.md`, `cycle_loop_design.md` | High | Completed (2025-12-03) | Core Maintainers | IR → Tiling → MemoryPlan → Schedule → CMDQ → ISA → Cycle Loop 단계별 artefact/규칙을 하나의 공통 예제(LLaMA block 등)로 문서화. `docs/README_SPEC.md`에 파이프라인 맵 섹션 추가 및 관련 스펙/디자인 문서들의 상호 참조를 정리하고, `docs/overview/dataflow_overview.md`에 MatMul+GELU 기준 end-to-end 예제(ONNX→IR→TileGraph→ScheduleDAG→CMDQ→Cycle Loop→Trace)를 추가했으며, IR/CMDQ 스펙(`npu_ir_spec.md`, `cmdq_format_spec.md`)과 StaticScheduler 설계 문서에서 동일 예제를 참조하도록 연결함 |
| [x] Timing/Quantization/Trace 스펙 연결 강화 | `docs/spec/timing/*.md`, `docs/spec/quantization/*.md`, `docs/spec/trace/*.md` | Medium | Completed (2025-12-03) | Core Maintainers | DMA timing 스펙에 예시 config/profile 스니펫을 추가하고, Quantization/Trace overview 스펙에서 IR/CMDQ/Timing/Trace 간 qbits/bytes/latency/metrics 필드 연계를 high-level로 명시해 Timing/Quant/Trace 계층 간 연결 관계를 정리함 |
| [x] Design 문서 상태/Owner/다이어그램 보강 | `docs/design/*.md` | Medium | Completed (2025-12-03) | Core Maintainers | Owner/Status 헤더를 정리하고, 핵심 모듈(CycleLoop, SimulatorCore, ControlFSM, DMAEngine)에 텍스트 기반 플로우/파이프라인 다이어그램을 추가해 Design 계층의 상위 구조를 보강함 |
| [x] Test 문서와 Spec/Design ID 매핑 정교화 | `docs/test/*.md`, `docs/spec/*.md`, `docs/design/*.md` | Medium | Completed (2025-12-03) | Core Maintainers | Unit/Integration/Performance/Golden 테스트 문서에 각 ID ↔ 관련 Spec/Design/ONNX/아티팩트 위치를 표로 정리(UT: 3.1, IT: 3.2, PV: 3.2, Golden: 3.2) |
| [x] Trace/Visualizer 워크플로우 튜토리얼 | `docs/spec/trace/*.md`, `docs/design/visualizer_design.md` | Low | Completed (2025-12-03) | Core Maintainers | Trace 생성 → Golden 비교 → 시각화 3단계 튜토리얼을 trace_format_spec.md(9.1)와 visualizer_design.md(6장)에 추가하여, 처음 보는 사람도 기본 워크플로우를 따라갈 수 있도록 정리함 |
