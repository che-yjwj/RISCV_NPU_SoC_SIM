# Documentation Study Milestone Plan — SDD 문서 1회독/정복 가이드
Status: Draft  
Owner: TBD (스터디 리더)  
Last Updated: 2025-12-05  

---

## 1. 목적
- `RISCV_NPU_SoC_SIM` 전체 문서를 효율적으로 읽고, 팀 내 공통 이해를 빠르게 확보하기 위한 단계별 스터디 마일스톤을 정의한다.
- 대상: 신규 기여자, 리뷰어, 구현 담당자. 시간 투자는 **총 4~5일(반나절~1일 단위)**를 가정한다.

---

## 2. 진행 원칙
- 문서 우선: `README.md`와 `docs/README_SPEC.md`의 우선순위 태그(필수/권장/참고)를 그대로 따른다.
- 얇은 단위: 하루(또는 반나절) 단위로 끝나는 범위로 나누고, 각 마일스톤마다 산출물(요약/의문점/연결관계 표)을 남긴다.
- 동일 예제 추적: LLaMA, MatMul→Tile→Schedule→CMDQ 예제가 반복되므로 **예제별 필드 흐름**을 표로 기록한다.
- 질문 리스트 관리: 읽는 동안 생긴 질문/모호점을 체크리스트로 쌓아 `docs/process/doc_improvement_tasks.md`와 연결한다.

---

## 3. 마일스톤 요약 (체크리스트)

- [ ] **M0. 준비 (0.5d)**  
  - 목표: 리딩 순서/노트 템플릿 확정.  
  - 읽기: `README.md`, `docs/README_SPEC.md` (목차/의존관계).  
  - 산출물: 개인 체크리스트(필수/권장/참고), 노트 템플릿(입력/출력/예제/질문 4칸).

- [ ] **M1. Overview 1st Pass (0.5~1d)**  
  - 목표: 전체 흐름과 블록 다이어그램 이해.  
  - 읽기: `docs/overview/system_architecture_overview.md`, `system_architecture.md`, `dataflow_overview.md`, 필요 시 `memory_noc_overview.md`, `module_responsibilities.md`.  
  - 산출물: ONNX→IR→Tile→CMDQ→Sim→Trace 한 줄 설명, 각 모듈 책임 요약, 이해한 흐름을 1페이지 메모로 정리.

- [ ] **M2. IR/CMDQ 핵심 스펙 (1d)**  
  - 목표: IR 구조와 CMDQ 포맷을 연결해 파이프라인의 중심 축을 잡는다.  
  - 읽기: `docs/spec/ir/npu_ir_spec.md`, `tensor_metadata_spec.md`, `quantization_ir_extension.md`, `docs/spec/isa/cmdq_overview.md`, `cmdq_format_spec.md`, `opcode_set_definition.md`.  
  - 산출물: IR 필드 ↔ CMDQ 필드 매핑 표, 공통 예제(예: LLaMA block) 필드 흐름 요약, 모호점 리스트.

- [ ] **M3. Timing/Quant/Trace 스펙 (1d)**  
  - 목표: 성능/계측 계층을 한 번에 정리.  
  - 읽기: `docs/spec/timing/*.md`, `docs/spec/quantization/*.md`, `docs/spec/trace/*.md`.  
  - 산출물: qbits→bytes→latency 관계 정리, Timeline/BW/Trace 필드 핵심 표, IR/CMDQ/Timing/Trace 연계 흐름 메모.

- [ ] **M4. Design 문서 (1d)**  
  - 목표: 스펙을 코드/엔진 관점으로 옮길 때의 책임과 인터페이스를 파악.  
  - 읽기: `docs/design/offline_compiler_design.md`, `ir_builder_design.md`, `tiling_planner_design.md`, `spm_allocator_design.md`, `static_scheduler_design.md`, `cmdq_generator_design.md`, `npu_simulator_core_design.md`, `cycle_loop_design.md`, `control_fsm_design.md`, `dma_engine_design.md`, `te_engine_design.md`, `ve_engine_design.md`, `visualizer_design.md`.  
  - 산출물: Pass/Engine별 입력/출력/주요 상태 변수 표, Cycle Loop 순서 메모.

- [ ] **M5. Test/예제/Trace 워크플로 (0.5~1d)**  
  - 목표: “무엇을 검증해야 하는지” 관점을 확보.  
  - 읽기: `docs/test/test_plan.md`, `unit_test_spec.md`, `integration_test_spec.md`, `performance_validation_protocol.md`, `golden_trace_examples.md`, `docs/spec/trace/gantt_timeline_spec.md`, `trace_format_spec.md`.  
  - 산출물: 테스트 ID ↔ Spec/Design 매핑 표, Golden Trace 워크플로 3단계 메모.

- [ ] **M6. 백로그 포커스 (선택, 0.5d)**  
  - 목표: 미완 항목(L2/LLC 등)만 별도 정리.  
  - 읽기: `docs/process/doc_improvement_tasks.md`의 L2/LLC 관련 문서 목록.  
  - 산출물: 요구 추가 필드/이벤트/정책 요약, 개선 PR 아이디어 초안.

---

## 4. 노트 템플릿 제안 (복사하여 사용)

```
문서: <path>
입력/출력: <이 문서가 전제하는 입력 / 정의하는 출력>
예제/표: <기억할 예제, 필드/파라미터>
연결: <앞/뒤로 이어지는 문서, 파이프라인 위치>
의문/백로그: <모호점, 개선 필요 지점>
```

---

## 5. 운영 팁
- 하루가 끝날 때마다 산출물을 한 군데(MD/스프레드시트)로 모아 `M0~M6` 체크박스를 업데이트한다.
- 이해가 어려운 부분은 `docs/process/doc_improvement_tasks.md`에 질문/백로그로 남기면 이후 문서 개선 때 활용 가능하다.
- 동일 예제를 기준으로 필드/파이프라인을 연결하면 전체 스택을 빠르게 재구성할 수 있다.
