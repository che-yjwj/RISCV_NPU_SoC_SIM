# Test Plan
**Path:** `docs/test/test_plan.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
본 문서는 NPU Simulator & Offline Compiler 전체 시스템에 대한 **테스트 전략과 범위**를 정의한다.  
각 테스트 종류(Unit/Integration/Performance/Regression)가 무엇을 검증하는지와,  
어떤 아티팩트를 관리해야 하는지를 명확히 한다.

## 2. 범위
- 포함:
  - Offline Compiler: IRBuilder/Tiling/SPMAllocator/StaticScheduler/CmdqGenerator.  
  - Simulator Core: ControlFSM, DMA/TE/VE/MemoryModel, Cycle Loop.  
  - Trace/Visualizer: Trace 포맷, 간단한 시각화 파이프라인 검증.  
- 제외:
  - ONNX 모델 학습/정확도(별도 ML pipeline).  
  - 실칩 HW 검증(이 프로젝트 범위 밖).

## 3. 테스트 항목/시나리오 (요약)
| ID   | 타입        | 설명                                           | 기대 결과                                   |
|------|------------|-----------------------------------------------|---------------------------------------------|
| T-UT-IR  | Unit   | IRBuilder가 간단한 ONNX MLP를 올바른 IR로 변환 | IR 구조/필드가 스펙과 일치                  |
| T-UT-DMA | Unit   | DMAEngine bytes/latency 계산 검증              | spec 공식과 동일한 latency/bytes           |
| T-IT-E2E | Integration | ONNX→CMDQ→Sim end-to-end 실행          | CMDQ 유효, Trace 생성, 오류 없이 종료      |
| T-PF-LLM | Performance | LLM workload에서 latency 예측 정확도    | 사전 정의된 허용 오차 범위 내              |
| T-RG-GOLD | Regression | Golden trace와 현재 trace 비교         | 차이가 없거나 허용 범위 내 diff            |

상세 케이스는 `unit_test_spec.md`, `integration_test_spec.md`, `performance_validation_protocol.md`, `golden_trace_examples.md`에서 정의한다.

### 3.1 대표 ID ↔ 스펙/디자인 문서 매핑

| Test ID   | 관련 Spec/Design 문서 |
| --- | --- |
| T-UT-IR   | `docs/spec/ir/npu_ir_spec.md`, `docs/design/ir_builder_design.md` |
| T-UT-DMA  | `docs/spec/timing/dma_timing_spec.md`, `docs/design/dma_engine_design.md` |
| T-IT-E2E  | `docs/overview/system_architecture.md`, `docs/spec/isa/cmdq_format_spec.md`, `docs/design/offline_compiler_design.md`, `docs/design/npu_simulator_core_design.md` |
| T-PF-LLM  | `docs/spec/timing/*.md`, `docs/spec/quantization/*.md`, `docs/test/performance_validation_protocol.md` |
| T-RG-GOLD | `docs/spec/trace/trace_format_spec.md`, `docs/test/golden_trace_examples.md` |

## 4. 절차 / 자동화
- 기본 실행 단계:
  1. 빌드/설정: 의존성 설치, 환경 변수 설정.  
  2. Unit Test: `tests/unit` 실행.  
  3. Integration Test: `tests/integration` 실행 (예: 샘플 ONNX→CMDQ→Sim).  
  4. Performance/Regression: 선택된 workload에 대해 시뮬레이션 후 결과 비교.  
- 도구/스크립트:
  - `make test`, `pytest`, 커스텀 스크립트(`tools/*`) 사용 권장.

## 5. 데이터 / 아티팩트 관리
- 입력 데이터:
  - `tests/data/onnx/*`: 샘플 모델.  
  - `tests/data/config/*`: 하드웨어/quantization 설정.  
- Golden 결과:
  - `tests/golden/cmdq/*`: CMDQ 스냅샷.  
  - `tests/golden/trace/*`: golden trace JSON.  
  - 관리 정책은 `golden_trace_examples.md` 참고.

## 6. 리뷰 / 승인 기준
- 새 기능/변경마다:
  - [ ] 최소 1개 Unit Test 또는 Integration Test 추가/수정.  
  - [ ] 관련 테스트 문서(`*_spec.md`)에 시나리오가 반영.  
  - [ ] CI에서 모든 테스트가 성공.  
  - [ ] 성능 영향이 있는 변경은 performance/regression 검증이 동반.

## 7. 향후 확장
- fuzzing/랜덤 workload 기반 stress 테스트.  
- 실측 결과와 비교하는 “hardware-in-the-loop” 검증 항목 추가.  
