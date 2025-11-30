
# Contribution Guide — IA_RISC_V_NPU_Simulator v2  
**Full Developer Contribution Guide (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

본 문서는 IA_RISC_V_NPU_Simulator v2 프로젝트에 기여하는 모든 개발자를 위한  
**공식 풀버전 기여 가이드(Contribution Guide)** 이다.

본 문서는 다음을 명확히 규정한다:

- 코드/문서/테스트 기여 원칙  
- 브랜치 전략  
- 커밋 메시지 규칙  
- PR 규칙 및 리뷰 프로세스  
- 코드 스타일 가이드(Python/Rust/Markdown)  
- 시뮬레이터 특성 상 반드시 지켜야 할 동기화 규칙  
- 테스트 환경 / 린트 환경 통합  
- 기여자 체크리스트

본 가이드는 프로젝트의 일관성, 재현성, 확장성을 보장하기 위한 **핵심 운영 문서**이다.

---

# 1. Repository Structure (요약)

IA_RISC_V_NPU_Simulator v2는 아래 디렉토리 구조를 따른다:

```
repo/
 ├─ src/
 │   ├─ npu_runtime/
 │   ├─ pyv/
 │   ├─ isa/
 │   ├─ scheduler/
 │   ├─ tiler/
 │   ├─ lowering/
 │   └─ utils/
 ├─ docs/
 │   ├─ prd/
 │   ├─ design/
 │   ├─ isa/
 │   ├─ examples/
 │   └─ dev/
 ├─ tests/
 │   ├─ unit/
 │   ├─ integration/
 │   └─ system/
 ├─ scripts/
 └─ tools/
```

---

# 2. Contribution Types

기여 종류는 다음과 같다:

### ✔ 1) 코드 기여
- Py‑V 연동  
- NPU Runtime (TE/VE/DMA/KV/NoC)  
- Tiler / Scheduler / Lowering  
- ISA Encoder/Decoder  
- Profiling / Logging / Timeline engine  

### ✔ 2) 문서 기여
- PRD/TDD 업데이트  
- 아키텍처 설명  
- ISA 스펙 확장  
- Example e2e 문서 추가  

### ✔ 3) 테스트 기여
- Unit tests  
- Integration tests  
- Regression tests  
- Golden reference 추가  

### ✔ 4) Issue/Proposal 기여
- Feature request  
- Bug report  
- 성능 개선 제안  

모든 기여는 PR(풀 리퀘스트) 기반으로 이루어진다.

---

# 3. Branching Strategy

본 프로젝트는 **GitHub Flow (Main Based)** 을 변형하여 사용한다.

### ✔ main
- production-ready  
- 모든 테스트 통과  
- 문서 완전성 필요  

### ✔ dev
- active development  
- 대부분의 PR은 dev로 merge  

### ✔ feature/\*
- 신규 기능 개발  
- ex) `feature/te-matmul-fusion`  

### ✔ bugfix/\*
- 버그 수정  
- ex) `bugfix/scheduler-lifetime-bug`  

### ✔ docs/\*
- 문서 업데이트 전용  

병렬 개발을 최대한 독립시키기 위해 feature 단위로 브랜치를 구성한다.

---

# 4. Commit Message Guidelines

모든 커밋은 다음 형식을 지켜야 한다:

```
<type>: <short description>
```

### 타입 규칙

| Type | 설명 |
|------|------|
| feat | 새로운 기능 추가 |
| fix | 버그 수정 |
| perf | 성능 개선 |
| refactor | 코드 구조 개선 (기능 변화 없음) |
| docs | 문서 변경 |
| test | 테스트 추가/수정 |
| build | 빌드/CI 관련 변경 |
| chore | 기타 자잘한 변경 |

### 예시

```
feat: add TE_QKT_TILE executor
fix: correct DMA burst alignment issue
docs: update ISA KV extension spec
refactor: separate SPM allocator from scheduler
test: add KV_LOAD_TILE range descriptor tests
```

---

# 5. Pull Request Rules

PR은 아래 요구사항을 만족해야 한다.

---

## 5.1 PR Template

PR은 다음 템플릿을 반드시 포함해야 한다:

```
### Summary
변경 요약

### Type of Change
(feat/fix/docs/test/refactor/chore)

### Related Issue
(issue number)

### Testing
- unit tests
- integration tests
- simulator run logs(optional)

### Checklist
- [ ] lint passed
- [ ] unit tests passed
- [ ] no timeline regression
- [ ] docs updated
```

---

## 5.2 PR Size

이 프로젝트는 아키텍처가 복잡하므로 **대규모 PR을 금지**한다.

- 400 lines 미만 권장  
- 800 lines 초과 PR → 거절 또는 분리 요청  

---

## 5.3 Review Rules

- 최소 1명 시니어 리뷰어 승인 필요  
- ISA 변경 시 2인 승인 필요  
- Scheduler 변경 시 2인 승인 필요  
- KV-extension 관련 변경 시 반드시 KV 리뷰어 배정  

---

# 6. Code Style Guide

## 6.1 Python Code Style

PEP8 기반 + 성능 중심 규칙:

- 함수 이름: `snake_case`  
- 클래스 이름: `CamelCase`  
- import 정렬  
- `typing` 적극 사용  
- assertion 대신 explicit error  
- long-running loop 내부에서 logging 최소화  

### 파이프라인 규칙
- tick loop 내부에서 allocation 금지  
- tile 객체는 불변(immutable) 구조 유지  

---

## 6.2 Rust Code Style (Optional backend)

- Clippy warnings 0  
- unsafe 금지  
- trait 기반 modular design  
- explicit lifetime 사용  

---

## 6.3 Markdown Style

- 80~100 char line width  
- fenced code blocks  
- Mermaid diagrams 사용 권장  
- 용어 통일 (TE/VE/DMA/SPM/KV/NoC)  

---

# 7. Testing Requirements for Contributions

PR merge 전 요구 테스트:

- Unit test pass  
- Integration test pass  
- E2E attention test pass  
- Timeline regression test pass  
- Memory snapshot diff zero  
- Py‑V instruction trace consistency  

만약 아래 항목이 발생하면 PR은 reject된다:

- KV-load scaling mismatch  
- Scheduler lifetime inconsistency  
- Sync/fence misplacement  
- DRAM overflow or out-of-bound access  

---

# 8. Performance Requirements

대규모 시뮬레이터이므로 성능 기여는 중요하다.

PR은 다음을 준수해야 한다:

- Python hot loop 최적화  
- unnecessary list allocation 금지  
- tile-level caching 적극 활용  
- Py-V tick loop 최소 branching  
- DRAM modeling에서 O(n) → O(1) 개선 시 우선 merge  

---

# 9. Documentation Requirements

문서 변경은 다음을 만족해야 한다:

- docs/ 디렉토리 내부의 해당 카테고리 명시  
- PRD/TDD/Design 문서와 내용 불일치 금지  
- Mermaid 다이어그램 파손 금지  
- ISA 스펙 변경 시 examples/와 lowering 문서도 업데이트  

---

# 10. Issue Reporting Rules

Issue 종류:

- bug report  
- performance degradation  
- documentation inconsistency  
- architecture proposal  
- feature request  

Issue에는 반드시 아래 포함:

- 어떤 레이어(tile/lowering/ISA/scheduler/runtime)인지  
- timeline dump (가능하면)  
- DRAM/SPM snapshot (가능하면)  
- 재현 조건  
- 기대 결과 vs 실제 결과  

---

# 11. Security / Consistency Rules

- ABI 변경 금지 (Py‑V ↔ NPU interface)  
- ISA semantics 변경 금지 (PRD 승인 필요)  
- scheduler internal ordering 변경은 반드시 regression test 필요  
- lowering rule 변경은 examples/ 문서까지 갱신 필수  

---

# 12. Contributor Checklist

PR 제출 전 다음 체크리스트를 만족해야 한다.

```
[ ] 코드 스타일 준수
[ ] typing 적용
[ ] 주석/문서 충실
[ ] tile 추상화 일관성 유지
[ ] lowering rule 검증
[ ] scheduler DAG 검증
[ ] SPM lifetime 정상
[ ] timeline regression 없음
[ ] DRAM/SPM snapshot diff 없음
[ ] unit/integration/system test 모두 통과
[ ] docs 업데이트 완료
```

---

# End of Document
