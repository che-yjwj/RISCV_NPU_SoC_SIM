# SDD Devflow Overview
**Path:** `docs/overview/sdd_devflow_overview.md`  
**Version:** v1.0  
**Status:** Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-03  

---

## 1. 목적 (Purpose)

이 문서는 `RISCV_NPU_SoC_SIM`에서 사용하는  
**Spec-Driven Development(SDD) 기반 개발 흐름(Devflow)**을 상위 수준에서 정리한다.

- 새 기능 추가, 버그 수정, 문서 개선 작업을 할 때  
  어떤 문서/파일을 어떤 순서로 다루어야 하는지를 한 페이지에서 보여준다.

상세 규칙과 템플릿은 다음 문서를 참고한다.

- `docs/process/spec_driven_development_workflow.md`  
- `docs/process/contribution_and_review_guide.md`  
- `docs/process/naming_convention.md`  
- `docs/process/versioning_and_changelog_guide.md`  
- `docs/process/milestone_plan.md`  
- `docs/process/vibe_coding_sdd_guide.md`

---

## 2. 공통 Devflow (기능 추가 기준)

기본 원칙: **Spec → Design → Test → Code → Doc/Changelog** 순서를 지킨다.

1. **Spec 정리**  
   - 관련 스펙 문서(`docs/spec/**`)에서 요구사항/인터페이스/포맷을 명시하거나 갱신한다.  
2. **Design 정리**  
   - 설계 문서(`docs/design/**`)에서 모듈 책임, 알고리즘 스케치, 데이터 구조를 정의한다.  
3. **Test 계획 연결**  
   - 테스트 문서(`docs/test/**`)에 테스트 ID/케이스/성공 기준을 추가한다.  
4. **코드 구현**  
   - `src/**`에서 Spec/Design에 정의된 구조에 맞추어 구현을 진행한다.  
5. **문서/Changelog 업데이트**  
   - 필요한 경우 overview/프로세스 문서를 갱신하고, 버전/변경 이력을 정리한다.

각 단계에서 어떤 체크리스트를 사용할지는  
`spec_driven_development_workflow.md`와 `contribution_and_review_guide.md`를 참고한다.

---

## 3. Doc-First 개선 작업 흐름

문서 품질 개선이나 아키텍처 리팩토링 아이디어는  
다음 세 문서를 중심으로 관리한다.

1. **리뷰 스냅샷**  
   - `docs/process/archive/review_by_chatgpt_v1.md` (archive)  
   - `docs/process/archive/review_by_chatgpt_v2.md` (archive)  
   → 전체 문서에 대한 AI 기반 리뷰 결과(그대로 보존).

2. **요약/기준선**  
   - `docs/process/documentation_review_summary.md`  
   → v1/v2 내용을 통합한 사람 친화적 요약본.

3. **실행 체크리스트**  
   - `docs/process/doc_improvement_tasks.md`  
   → 실제로 진행할 문서 개선 Task 목록(Completed/Backlog).

개선 작업을 시작할 때는:

1. 손보고 싶은 영역의 리뷰 요약을 확인하고(summary).  
2. `doc_improvement_tasks.md`에서 기존 Task를 선택하거나 새 항목을 추가한 뒤.  
3. 관련 Spec/Design/Test 문서를 열어 Codex/Vibe Coding 세션을 진행한다.

자세한 사용 예시는 `vibe_coding_sdd_guide.md` 마지막 섹션을 참고한다.

---

## 4. Milestone/Task 기반 진행

장기적인 Phase/Task 관리는 `docs/process/milestone_plan.md`에서 담당한다.

- Phase 단위(예: “MatMul-only E2E”, “LLM Prefill/Decode”, “Timing 정교화”)로 큰 목표를 정의.  
- 각 Phase 아래에 개별 Task와 Done Criteria, 관련 Spec/Design/Test 링크를 명시.  
- 실제 구현 시:
  - Milestone Plan에서 Task 선택  
  - 관련 문서 업데이트  
  - 코드/테스트/문서/Changelog까지 완료 후 체크

Codex/Vibe Coding 세션 예시는  
`vibe_coding_sdd_guide.md` 3~6장에서 단계별로 정리되어 있다.

---

## 5. 요약 플로우 (Text Diagram)

```text
[아이디어 / 요구사항]
      │
      ▼
[Spec 문서 업데이트]
      │
      ▼
[Design 문서 업데이트]
      │
      ▼
[Test 문서 연결 (ID/케이스)]
      │
      ▼
[코드 구현 (src/**)]
      │
      ▼
[테스트 실행 및 수정]
      │
      ▼
[문서/Changelog 정리]
```

문서 중심 Devflow를 통해,  
**“코드가 스펙에서 벗어나지 않도록”** 하고,  
장기적으로도 아키텍처/문서/코드가 함께 진화할 수 있는 구조를 유지한다.
