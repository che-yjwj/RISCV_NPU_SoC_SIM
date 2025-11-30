# Versioning & Changelog Guide
**Path:** `docs/process/versioning_and_changelog_guide.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
스펙/코드/테스트의 변경 이력을 체계적으로 관리하여  
어떤 버전에서 어떤 변경이 이루어졌는지 추적 가능하게 한다.

## 2. 핵심 원칙
- **Semantic Versioning 참고**: `MAJOR.MINOR.PATCH` 의미를 유지.  
- **Spec 우선 버전**: 핵심 스펙(IR/ISA/Timing/Trace)이 버전을 주도, 코드는 이에 맞춰간다.  
- **모든 breaking change 기록**: 호환성 깨지는 변경은 반드시 Changelog에 명시한다.

## 3. 버전 규칙 (예시)
- **Spec 패키지 버전**:  
  - ex) `spec_version: 1.0.0`  
  - IR/ISA/Timing/Trace 스펙에 공통 적용.  
- **코드/릴리즈 버전**:  
  - ex) `sim_version: 0.1.0`  
  - 구현/도구/CLI 버전에 사용.
- 변경 유형:
  - MAJOR: IR/ISA/Trace 구조 변경 등, 이전 CMDQ/Trace와 비호환.  
  - MINOR: 새로운 opcode/필드 추가(뒤 호환).  
  - PATCH: 버그/설명 수정, 인터페이스 동일.

## 4. Changelog 작성 가이드
- 위치: `CHANGELOG.md` 또는 관련 모듈별 Changelog.  
- 형식 예시:
```markdown
## [1.1.0] - 2025-01-10
### Added
- New opcode `TE_SPARSE_GEMM_TILE` (spec/isa/opcode_set_definition.md).

### Changed
- Update TE timing spec to support sparsity ratio.

### Fixed
- Clarified trace_format_spec for MEM_ACCESS_EVENT.
```

## 5. 절차 / 체크리스트
- [ ] breaking change 여부 판단 (스펙/코드/데이터).  
- [ ] 해당하는 버전 필드 업데이트 (`spec_version`, `sim_version`).  
- [ ] Changelog 섹션 추가/수정.  
- [ ] README/README_SPEC 등에 새로운 버전 설명 반영.

## 6. 검증 / 리뷰 포인트
- PR에서 버전 증가가 필요한데 누락되지 않았는가?  
- Changelog 항목이 구체적인가(어떤 파일/스펙/기능이 바뀌었는지)?.  
- 호환성 영향(마이그레이션 필요 여부)이 명시되어 있는가?

## 7. 향후 업데이트 계획
- 모듈별(Compiler/Simulator/Visualizer) 버전 정책 정교화.  
- 자동 Changelog 생성 도구와 연동(태그/커밋 메시지 기반).  
