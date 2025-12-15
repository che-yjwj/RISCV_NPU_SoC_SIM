# tile_based → 메인 문서 흡수 매핑

**Status:** Completed  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

본 문서는 과거 `docs/tile_based/` 트리의 문서들을 메인 문서 트리(`docs/overview|spec|design|process|test`)로
흡수/통합하기 위한 “목표 위치 매핑”을 기록한다.

현재 상태:
- 통합 완료(파일 단위 이관 완료).
- `docs/tile_based/` 트리는 스텁 포함 전체 제거됨(메인 문서만 유지).

원칙(통합 당시):
- 메인 트리(`docs/spec/*`)가 규범의 단일 소스 오브 트루스(SSoT).
- 파일 단위로 순차 통합하며, 한 번에 하나의 문서만 “SSoT”로 승격한다.

---

## 1) 매핑 테이블

| tile_based 파일 | 흡수 목표 위치(메인) | 방식 | 상태 |
|---|---|---|---|
| `docs/tile_based/spec/architecture/tile_lifecycle.md` (deleted) | `docs/spec/architecture/tile_semantics_spec.md` (Lifecycle 섹션 확장) | merge then delete | 완료 |
| `docs/tile_based/spec/architecture/memory_hierarchy.md` (deleted) | `docs/spec/architecture/tile_semantics_spec.md` (Memory 섹션 확장) | merge then delete | 완료 |
| `docs/tile_based/spec/architecture/dataflow_te_ve.md` (deleted) | `docs/spec/architecture/tile_semantics_spec.md` (TE–VE/STB 섹션 확장) | merge then delete | 완료 |
| `docs/tile_based/spec/architecture/compute_engines.md` (deleted) | `docs/spec/architecture/tile_semantics_spec.md` (TE/VE 역할 경계 확장) | merge then delete | 완료 |
| `docs/tile_based/spec/architecture/KV_cache_tiling_strategy_spec.md` (deleted) | `docs/spec/architecture/kv_cache_semantics_spec.md` | split+merge then delete | 완료 |
| `docs/tile_based/spec/contracts/tile_contract.md` (deleted) | `docs/spec/architecture/tile_contract_spec.md` | merge then delete | 완료 |
| `docs/tile_based/spec/scheduling/static_scheduler_spec.md` (deleted) | `docs/spec/scheduling/static_scheduler_semantics_spec.md` + `docs/design/static_scheduler_design.md` | spec/design 분리 후 merge then delete | 완료 |
| `docs/tile_based/spec/scheduling/prefill_decode_workload_mapping.md` (deleted) | `docs/overview/dataflow_overview.md`(LLM 섹션) + `docs/spec/scheduling/prefill_decode_workload_semantics_spec.md` | split+merge then delete | 완료 |
| `docs/tile_based/spec/ir/npu_ir_core_spec.md` (deleted) | `docs/design/npu_ir_core_reference.md` (메인 IR 대체 아님) | move then delete | 완료 |
| `docs/tile_based/spec/ir/npu_ir_lowering_and_execution.md` (deleted) | `docs/design/cmdq_generator_design.md`, `docs/design/static_scheduler_design.md`, `docs/design/cycle_loop_design.md` | split+merge then delete | 완료 |
| `docs/tile_based/spec/ir/tile_ir_spec.md` (deleted) | `docs/spec/ir/tile_ir_optional_spec.md` | move then delete | 완료 |
| `docs/tile_based/design/analysis/tile_rt_analysis_for_npu_simulator.md` (deleted) | `docs/design/tile_rt_analysis.md` | move then delete | 완료 |
| `docs/tile_based/test/examples/pytorchsim_npu_ir_examples.md` (deleted) | `docs/test/examples/pytorchsim_npu_ir_examples.md` | move then delete | 완료 |
| `docs/tile_based/test/examples/tutorial_minimal_llama_to_tile_npu.md` (deleted) | `docs/test/examples/tutorial_minimal_llama_to_tile_npu.md` | move then delete | 완료 |
| `docs/tile_based/README.md` (deleted) | `docs/README_SPEC.md`에 통합 | merge then delete | 완료 |

---

## 2) 순차 진행 규칙(권고)

1. “충돌 적고 독립적인 문서”부터 이동(예제/체크리스트/인덱스).
2. 스펙 승격은 항상 “메인 스펙에 merge” 순서로 진행.
3. 링크 정리 기준:
   - 메인 문서는 절대경로(`docs/...`) 링크 허용
   - tile_based 문서는 상대경로 링크 권장(리포 내부 이동에 강함)
