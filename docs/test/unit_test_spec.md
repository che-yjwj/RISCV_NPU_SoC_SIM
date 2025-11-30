# Unit Test Specification
**Path:** `docs/test/unit_test_spec.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
개별 모듈(함수/클래스) 단위에서 **로직이 스펙과 일치하는지 빠르게 검증**하기 위한 유닛 테스트 항목을 정의한다.

## 2. 범위
- 포함:
  - IRBuilder, QuantizationAnnotator, TilingPlanner, SpmAllocator.  
  - StaticScheduler, CmdqGenerator.  
  - DMAEngine, TensorEngine, VectorEngine, MemoryModel.  
- 제외:
  - End-to-end 동작(Integration Test에서 다룸).  
  - 성능/정확도 지표(Performance Validation에서 다룸).

## 3. 테스트 항목/시나리오 (예시)
| ID        | 모듈          | 설명                                           | 기대 결과                        |
|-----------|---------------|-----------------------------------------------|----------------------------------|
| UT-IR-01  | IRBuilder     | 단순 MLP ONNX → NPU IR 변환                    | LayerIR/TensorIR 스펙과 일치     |
| UT-DMA-01 | DMAEngine     | qbits/num_elements로 bytes 계산 검증           | spec 수식과 동일한 bytes_total  |
| UT-DMA-02 | DMAEngine     | alignment 적용 후 bytes_aligned 검증          | alignment 규칙 준수              |
| UT-TE-01  | TensorEngine  | MACs, latency 계산 공식 검증                  | te_timing_spec와 동일            |
| UT-VE-01  | VectorEngine  | LN/Softmax latency 계산 공식 검증             | ve_timing_spec와 동일            |
| UT-SPM-01 | SpmAllocator  | tile bytes가 bank 용량을 넘지 않는지 확인     | allocation 성공, 예외 없음       |

필요 시 각 모듈별로 UT 케이스를 계속 확장한다.

## 4. 절차 / 자동화
- 테스트 실행:
  - `pytest tests/unit` 또는 이에 상응하는 커맨드.  
- 각 UT 파일은 하나의 모듈에 집중:
  - `tests/unit/test_ir_builder.py`, `test_dma_engine.py` 등.

## 5. 데이터 / 아티팩트 관리
- 간단한 테스트 데이터는 코드 내 fixture/inline 데이터 사용.  
- 복잡한 입력(ONNX 등)은 `tests/data/unit/`에 저장.

## 6. 리뷰 / 승인 기준
- 새 모듈/기능 추가 시:
  - [ ] 최소 1개 이상의 UT가 추가되었는가?  
  - [ ] 실패 케이스/에지 케이스(잘못된 입력)에 대한 UT가 있는가?  
  - [ ] UT 이름이 시나리오를 잘 설명하는가?

## 7. 향후 확장
- Property-based testing (예: Hypothesis) 도입 검토.  
- fuzz 입력을 통한 예외 처리/오류 경로 테스트.  
