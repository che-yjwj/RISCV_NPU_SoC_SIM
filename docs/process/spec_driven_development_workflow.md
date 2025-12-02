# Spec-Driven Development Workflow
**Path:** `docs/process/spec_driven_development_workflow.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
이 문서는 본 프로젝트에서의 **Spec-Driven Development(SDD)** 기본 흐름을 정의한다.  
모든 기능/변경은 “스펙 → 디자인 → 구현 → 테스트 → 리뷰” 단계가 문서로 남도록 하는 것이 목표다.

## 2. 핵심 원칙
- **문서 우선**: 코드 변경 전 관련 Spec/Design/Test 문서부터 업데이트한다.  
- **단일 출처**: IR/CMDQ/Timing/Trace의 형식·의미는 반드시 대응 스펙에서 정의한다.  
- **테스트 동반**: 기능 추가/변경 시 최소 1개의 테스트 시나리오가 문서에 반영된다.  
- **리뷰 가능성**: 리뷰어가 문서만 보고 변경 의도를 이해할 수 있어야 한다.

## 3. 절차 / 체크리스트

### 3.1 단계 요약
1. **Spec 업데이트**  
   - 관련 스펙 파일(e.g. `docs/spec/...` 또는 `README_SPEC.md`)을 수정.  
2. **Design 업데이트**  
   - 해당 모듈의 디자인 문서(e.g. `docs/design/...`)에 구조/알고리즘/인터페이스를 반영.  
3. **Test 문서 업데이트**  
   - `docs/test/*.md`에 새로운 시나리오/케이스를 추가.  
4. **구현**  
   - `src/...`에 실제 코드를 작성하고, 테스트 코드를 `tests/...`에 추가.  
5. **리뷰 & 머지**  
   - PR에 변경된 Spec/Design/Test 링크 첨부, 리뷰어가 문서와 코드의 일치 여부를 확인.

### 3.2 체크리스트
- [ ] 이 변경과 직접 관련된 Spec 파일은 모두 찾았는가?  
- [ ] 디자인 문서에 인터페이스/데이터 플로우가 설명되어 있는가?  
- [ ] 최소 1개 이상의 테스트 시나리오가 문서/테스트 코드에 존재하는가?  
- [ ] README_SPEC/Index에 새 문서/파일이 반영되었는가?

## 4. 권장 템플릿 / 예시
- Spec: `docs/spec/..`에 있는 패턴(목적, 범위, 설계 원칙, 예제, 참조 문서)을 그대로 사용.  
- Design: 기존 디자인 문서 템플릿(목적, 책임, 내부 구조, 플로우, 인터페이스, 예시)을 재사용.  
- Test: `test_plan.md`, `unit_test_spec.md`, `integration_test_spec.md`의 표 형식을 사용.

### 4.1 PR/Issue 템플릿 연계 예시

- **Spec 변경 관련 Issue 제목 규칙**
  - `[SPEC] IR timing update for TE`  
  - `[SPEC] Add KV cache quantization fields`
- **Spec 변경 포함 PR 제목 규칙**
  - `[spec][ir] Update npu_ir_spec for KV4`  
  - `[spec][isa] Extend CMDQ deps fields`
- GitHub Issue/PR 템플릿에 다음 체크 항목을 두는 것을 권장:
  - [ ] 관련 스펙 문서 경로를 적었는가?  
  - [ ] Design/Test 문서도 함께 업데이트했는가?

## 5. 검증 / 리뷰 포인트
- Spec이 변경된 코드/테스트와 실제 일치하는지.  
- 새로운 필드/옵션이 생긴 경우 README_SPEC 및 관련 문서들이 모두 갱신되었는지.  
- 테스트가 스펙에 언급된 요구사항을 충분히 커버하는지(기능/에러/성능 등).  
- Breaking change인 경우 버전/호환성 전략이 명시되었는지.

## 6. 향후 업데이트 계획
- CI에서 문서 구조/상태(complete/in_progress)를 자동 체크하도록 스크립트 연동.  
- 주요 기능별 “예시 흐름”을 SDD 관점에서 정리한 가이드 추가.  
