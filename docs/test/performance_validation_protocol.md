# Performance Validation Protocol
**Path:** `docs/test/performance_validation_protocol.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
시뮬레이터의 **성능/정확도(특히 latency·bandwidth 예측)**가 스펙에서 정의한 목표를 충족하는지 검증하는 절차를 정의한다.

## 2. 범위
- 포함:
  - latency 예측 정확도 (실측/레퍼런스 대비 ±허용 오차).  
  - DRAM/Bus bandwidth 사용 패턴의 현실성.  
  - 엔진 utilization/병목 분석의 정합성.  
- 제외:
  - 모델 정확도(metric: perplexity, accuracy 등) 자체.

## 3. 테스트 항목/시나리오 (예시)
| ID        | 워크로드      | 설명                                      | 기대 결과                        |
|-----------|---------------|------------------------------------------|----------------------------------|
| PV-MLP-01 | Small MLP     | 단순 feed-forward network latency 검증   | 오차율 ≤ 10%                     |
| PV-ATTN-01| Self-Attention| attention + KV cache의 latency/profiling | 오차율 ≤ 15%                     |
| PV-LLM-01 | LLM block     | Prefill/Decode 전체 latency 및 BW 패턴   | 규정된 오차/패턴 범위 내         |

“실측”은 레퍼런스 시뮬레이터/분석 또는 하드웨어 측정 값을 의미할 수 있다.

## 4. 절차 / 자동화
- 입력:
  - workload 정의(모델, 시퀀스 길이, bitwidth, 엔진 구성).  
  - reference 결과(또는 기준 수식 결과).  
- 절차:
  1. 시뮬레이터 실행 → Trace + summary_metrics 생성.  
  2. reference 결과와 비교:
     - latency_total, per-layer latency, bandwidth usage 등.  
  3. 오차/편차 계산:
     - `abs(sim - ref) / ref`.  
  4. 허용 범위 내인지 판정, 보고서 생성.
- 자동화:
  - `tests/perf/test_*.py` 혹은 `tools/perf_validate.py` 등에서 위 과정을 자동화.

## 5. 데이터 / 아티팩트 관리
- 입력:
  - `tests/data/perf/*`: 모델/구성.  
- 출력:
  - `tests/artifacts/perf_results/*.json`: 실제 vs reference vs diff.  
  - 장기적으로는 시계열로 관리하여 회귀/향상 여부를 확인.

## 6. 리뷰 / 승인 기준
- 새로운 timing/스케줄링/메모리 모델 변경 시:
  - [ ] 성능 검증 시나리오를 다시 실행했는가?  
  - [ ] 오차가 증가한 경우 이유가 문서/PR에 설명되어 있는가?  
  - [ ] 허용 오차를 넘어서는 경우 spec/디자인을 먼저 업데이트했는가?

## 7. 향후 확장
- power/energy 추정 모델을 포함한 에너지 효율 검증.  
- 다양한 하드웨어 config와 workload matrix에 대한 자동 성능 회귀 테스트.  
