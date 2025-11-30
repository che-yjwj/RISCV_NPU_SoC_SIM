# Naming Convention
**Path:** `docs/process/naming_convention.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
IR 필드, CMDQ opcode/필드, 코드(클래스/함수/파일) 이름을 일관되게 유지해  
스펙/코드/테스트 간 추적 가능성과 가독성을 높인다.

## 2. 핵심 원칙
- **의미 우선**: 이름만 보고 역할을 유추할 수 있어야 한다.  
- **일관성**: 같은 개념은 모든 층(스펙, 코드, 테스트)에서 같은 이름을 사용한다.  
- **축약 최소화**: 지나친 약어는 피하고, 필요 시 문서에서 약어 정의를 제공한다.

## 3. 규칙 요약

### 3.1 IR / CMDQ 필드
- JSON 키: `snake_case` 사용  
  - 예: `qbits_weight`, `tensor_role`, `deps_before`.  
- ID 문자열: `lower_snake` + 숫자 또는 명시적 태그  
  - 예: `ffn_2`, `attn_block3_q_proj`.  
- role 값: 소문자, 의미 있는 단어  
  - 예: `"activation"`, `"weight"`, `"kv"`, `"embedding"`.

### 3.2 코드 (Python 가정)
- 파일/모듈: `snake_case`  
  - 예: `dma_engine.py`, `static_scheduler.py`.  
- 클래스: `CamelCase`  
  - 예: `DmaEngine`, `StaticScheduler`, `IrBuilder`.  
- 함수/메서드/지역 변수: `snake_case`  
  - 예: `build_ir`, `plan_tiles`, `allocate_spm`.  
- 상수: `UPPER_SNAKE_CASE`.

### 3.3 테스트 이름
- 파일: `test_<module>.py`  
  - 예: `test_dma_engine.py`.  
- 테스트 함수: `test_<scenario>_<expected>`  
  - 예: `test_dma_load_tile_bytes_aligned`.

## 4. 체크리스트
- [ ] IR 스펙과 코드에서 동일한 필드명을 사용했는가? (`qbits_weight` vs `qbits_w` 같은 혼동 방지)  
- [ ] opcode, op_type, layer_id 등 핵심 문자열이 문서/코드/trace에서 일치하는가?  
- [ ] 파일/클래스/함수 이름이 역할을 충분히 설명하는가?

## 5. 검증 / 리뷰 포인트
- PR 리뷰 시, 새로 등장한 이름이 이 규칙을 따르는지 확인.  
- 기존 이름과 충돌하거나 두 가지 형태가 섞여 있지 않은지 점검.  
- 필요 시 naming 변경은 별도 리팩토링 PR로 분리해 영향 범위를 명확히 한다.

## 6. 향후 업데이트 계획
- 언어별(Python/C++ 등) 세부 스타일 가이드 연결.  
- 대규모 리팩토링 시 naming 변경 체크리스트 추가.  
