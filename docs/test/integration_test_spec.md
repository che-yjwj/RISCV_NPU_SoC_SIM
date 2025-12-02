# Integration Test Specification
**Path:** `docs/test/integration_test_spec.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
Offline Compiler와 Simulator Core를 포함한 **엔드-투-엔드 및 모듈 통합 테스트**를 정의한다.  
“ONNX → CMDQ → Simulator → Trace” 전체 플로우가 문서/스펙과 일치하는지 확인하는 것이 목표다.

## 2. 범위
- 포함:
  - ONNX 입력부터 CMDQ, Trace 생성까지의 full path.  
  - Compiler 모듈 간 상호작용(IR, TileGraph, SPM, Schedule).  
  - Simulator Core의 CMDQ 실행 및 trace 출력.  
- 제외:
  - UI/시각화 레이어(별도 E2E 테스트에서 다룰 수 있음).

## 3. 테스트 항목/시나리오 (예시)
| ID        | 설명                                              | 기대 결과                                   |
|-----------|--------------------------------------------------|---------------------------------------------|
| IT-MLP-01 | 작은 MLP ONNX → CMDQ → Sim 실행                  | CMDQ 유효, Trace 생성, 오류 없이 종료      |
| IT-ATTN-01| 간단한 Self-Attention 블록 End-to-End           | TE/VE/DMA timeline이 spec 데이터플로우와 일치 |
| IT-KV-01  | KV Cache 포함 LLM Prefill/Decode 패턴 검증       | KV traffic/bitwidth가 spec과 일관           |
| IT-ERR-01 | 잘못된 CMDQ/IR 입력에 대한 에러 핸들링 확인     | 명확한 에러 메시지, 비정상 종료 없음       |

### 3.1 대표 ONNX 모델 및 메트릭 예시

| ID        | ONNX 모델 예시 | 주요 메트릭 | 비고 |
| --- | --- | --- | --- |
| IT-MLP-01  | `tests/data/integration/onnx/mlp_small.onnx` | 총 cycle 수, TE/VE utilization, DRAM bytes | 단일 FFN 블록 기준 |
| IT-ATTN-01 | `tests/data/integration/onnx/attn_block.onnx` | attention block latency, KV traffic bytes | Self-Attention 데이터플로우 검증 |
| IT-KV-01   | `tests/data/integration/onnx/llm_prefill_decode.onnx` | prefill/decode latency per token, KV bytes | Prefill/Decode 패턴 및 KV 재사용 확인 |
| IT-ERR-01  | 의도적으로 잘못된 CMDQ/IR 스냅샷 | 에러 코드/메시지 | 에러 경로·검증 로직 테스트 |

## 4. 절차 / 자동화
- 실행 단계:
  1. 테스트용 ONNX/Config 준비 (`tests/data/integration`).  
  2. Offline Compiler 실행 → CMDQ 출력.  
  3. Simulator 실행 → Trace 출력.  
  4. Trace/summary를 Golden 또는 기대 범위와 비교.  
- 도구/스크립트:
  - `tests/integration/test_*.py`에서 위 과정을 자동화.  
  - 필요 시 `tools/*`에 helper 스크립트 배치.

## 5. 데이터 / 아티팩트 관리
- 입력:
  - `tests/data/integration/onnx/*.onnx`  
  - `tests/data/integration/config/*.yaml`  
- 출력:
  - CMDQ: `tests/artifacts/cmdq/*`  
  - Trace: `tests/artifacts/trace/*`  
  - 일부는 `golden_trace_examples.md`에 정의된 golden set과 공유.

## 6. 리뷰 / 승인 기준
- 새로운 워크로드/기능이 추가되면:
  - [ ] 적어도 하나의 Integration Test가 해당 플로우를 검증하는가?  
  - [ ] 실패 시 원인 파악이 가능한 로그/trace가 남는가?  
  - [ ] CI에서 Integration Test가 기본적으로 실행되는가?

## 7. 향후 확장
- 다양한 하드웨어 config 조합(엔진 수, bitwidth, SPM 크기)에 대한 matrix 테스트.  
- stress test (긴 sequence, 큰 모델)용 integration 시나리오 추가.  
