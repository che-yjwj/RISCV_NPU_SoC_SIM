# Tile-based NPU 문서 인덱스

타일 기반 NPU 아키텍처/IR/스케줄링 문서를 한 곳에서 찾을 수 있도록
폴더 구조와 주요 문서를 안내한다.

## 폴더 구조

`docs/README_SPEC.md`의 상위 구조(overview/spec/design/process/test)를
`docs/tile_based/`에도 동일하게 적용한다.

- `overview/` : 타일 기반 접근의 배경/개요 (필요 시 확장)
- `spec/` : 타일 기반 구조의 핵심 스펙
  - `spec/architecture/` : 아키텍처 불변 규칙 (메모리, 라이프사이클, 데이터플로우, 엔진, KV 타일링)
  - `spec/contracts/` : HW–SW 경계 계약(Contract)
  - `spec/ir/` : Tile IR 및 NPU-IR 스펙/로어링/실행 의미론
- `spec/scheduling/` : lowering + static scheduling 규칙, Prefill/Decode 워크로드 매핑
- `design/` : 구현 설계 및 모델링 문서 (분석 포함)
  - `design/analysis/` : TileRT 관점 분석, 성능/모델링 연구 메모
- `process/` : 타일 기반 문서/개발 프로세스(필요 시 확장)
- `test/` : 예제/회귀 기준 및 검증 자료
  - `test/examples/` : IR 예제 및 튜토리얼

## 핵심 진입점

- 아키텍처 규칙: `spec/architecture/memory_hierarchy.md`, `spec/architecture/tile_lifecycle.md`, `spec/architecture/dataflow_te_ve.md`, `spec/architecture/compute_engines.md`, `spec/architecture/KV_cache_tiling_strategy_spec.md`
- 계약: `spec/contracts/tile_contract.md`
- 스케줄링: `spec/scheduling/static_scheduler_spec.md`, `spec/scheduling/prefill_decode_workload_mapping.md`
- IR 스펙: `spec/ir/npu_ir_core_spec.md`, `spec/ir/tile_ir_spec.md`, `spec/ir/npu_ir_lowering_and_execution.md`
- 예시/튜토리얼: `test/examples/pytorchsim_npu_ir_examples.md`, `test/examples/tutorial_minimal_llama_to_tile_npu.md`
- 분석: `design/analysis/tile_rt_analysis_for_npu_simulator.md`
