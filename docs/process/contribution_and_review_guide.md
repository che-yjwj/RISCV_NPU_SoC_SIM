# Contribution & Review Guide
**Path:** `docs/process/contribution_and_review_guide.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
이 문서는 기여자와 리뷰어가 **Spec-Driven Development 흐름에 맞춰 작업·리뷰**할 수 있도록 절차와 기준을 정의한다.

## 2. 핵심 원칙
- **Spec 링크 필수**: 모든 PR은 관련 스펙/디자인/테스트 문서 링크를 포함한다.  
- **작은 단위 변경**: 한 PR은 가능한 한 기능 하나 또는 작은 논리 단위에 집중한다.  
- **테스트 동반**: 코드 변경에는 가능한 한 테스트 추가/수정이 포함되어야 한다.  
- **투명한 결정**: 중요한 설계 결정은 문서에 기록하고 PR에서 요약한다.

## 3. 절차 / 체크리스트

### 3.1 기여자(Author)
1. 변경 범위 파악  
   - 관련 스펙/디자인/테스트 문서를 찾고 필요한 업데이트를 선행.  
2. 구현 & 테스트  
   - 코드 및 테스트를 작성하고, 로컬에서 테스트 실행.  
3. PR 생성  
   - 제목: `[area] short description`.  
   - 설명: 변경 요약, 동기, 관련 문서 링크, 테스트 결과(간단 로그 포함).  
4. Self-check  
   - [ ] Spec/Design/Test 문서가 최신인가?  
   - [ ] 불필요한 파일 변경/포맷팅이 없는가?  
   - [ ] CI가 통과하는가?

### 3.2 리뷰어(Reviewer)
- [ ] 관련 스펙/디자인 문서와 코드가 일치하는지 확인.  
- [ ] 인터페이스/이름/구조가 naming convention과 일치하는지.  
- [ ] 테스트가 충분한지, 누락된 에지케이스는 없는지.  
- [ ] 유지보수성/확장성 측면에서 문제가 없는지(과도한 coupling 등).  
- [ ] breaking change의 경우 versioning/changelog 가이드에 맞게 처리됐는지.

### 3.3 최소 리뷰 규칙 (권장)

- Spec/Design 변경이 포함된 PR:
  - 최소 2명 승인 (아키텍트/모듈 오너 1명 포함 권장).
- 구현/버그 수정 PR:
  - 최소 1명 승인, 가능하면 해당 모듈에 익숙한 리뷰어 우선 지정.
- 테스트만 추가/수정하는 PR:
  - 상황에 따라 self-merge 가능하나, 회귀 위험이 크면 리뷰 권장.

PR 생성 시 라벨 예시:
- `type:spec`, `type:design`, `type:impl`, `type:test`
- `area:compiler`, `area:simulator`, `area:docs`

## 4. 권장 템플릿 / 예시

### 4.1 PR 설명 템플릿
```text
## Summary
- 무엇을 변경했는지 한두 줄 요약

## Motivation
- 왜 이 변경이 필요한지

## Related Docs
- Spec: docs/spec/...
- Design: docs/design/...
- Test: docs/test/...

## Testing
- [ ] pytest tests/unit/... (pass)
- 기타
```

## 5. 검증 / 리뷰 포인트
- PR에 문서 링크가 포함되어 있는지.  
- 변경이 기존 설계 원칙을 깨지 않는지.  
- breaking change의 경우 버전/마이그레이션 문서가 있는지.  
- 리뷰 코멘트에 대한 대응이 적절히 처리되었는지(추가 커밋/추가 설명 등).

## 6. 향후 업데이트 계획
- 역할별(아키텍트/리뷰어/초보 기여자) 가이드 세분화.  
- “좋은 PR/나쁜 PR” 예시 추가.  
