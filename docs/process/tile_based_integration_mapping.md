# tile_based → 메인 문서 흡수 매핑

**Status:** Active  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-14

본 문서는 `docs/tile_based/` 트리의 문서들을 메인 문서 트리(`docs/overview|spec|design|process|test`)로
흡수/통합하기 위한 “목표 위치 매핑”을 정의한다.

원칙:
- 메인 트리(`docs/spec/*`)가 규범의 단일 소스 오브 트루스(SSoT).
- `docs/tile_based/*`는 통합 진행 중에는 원문을 유지하되, 상단에 “승격됨/이관됨” 링크를 둔다.
- 파일 단위로 순차 통합하며, 한 번에 하나의 문서만 “SSoT”로 승격한다.

---

## 1) 매핑 테이블

| tile_based 파일 | 흡수 목표 위치(메인) | 방식 | 상태 |
|---|---|---|---|
| `docs/tile_based/spec/architecture/tile_lifecycle.md` | `docs/spec/architecture/tile_semantics_spec.md` (Lifecycle 섹션 확장) | merge + tile_based에 링크 유지 | 진행중 |
| `docs/tile_based/spec/architecture/memory_hierarchy.md` | `docs/spec/architecture/tile_semantics_spec.md` (Memory 섹션 확장) | merge + tile_based에 링크 유지 | 진행중 |
| `docs/tile_based/spec/architecture/dataflow_te_ve.md` | `docs/spec/architecture/tile_semantics_spec.md` (TE–VE/STB 섹션 확장) | merge + tile_based에 링크 유지 | 진행중 |
| `docs/tile_based/spec/architecture/compute_engines.md` | `docs/spec/architecture/tile_semantics_spec.md` (TE/VE 역할 경계 확장) | merge + tile_based에 링크 유지 | 진행중 |
| `docs/tile_based/spec/architecture/KV_cache_tiling_strategy_spec.md` | `docs/spec/architecture/` 내 신규 `kv_cache_semantics_spec.md` 또는 `docs/spec/ir/npu_ir_spec.md`의 KV 섹션 + `docs/spec/timing/*` | split+merge (규범/파라미터 분리) | 보류 |
| `docs/tile_based/spec/contracts/tile_contract.md` | `docs/spec/architecture/` 또는 `docs/spec/isa/`(CMDQ 필드 계약) | 정합성 수정 후 merge | 보류 |
| `docs/tile_based/spec/scheduling/static_scheduler_spec.md` | `docs/spec/` 내 신규 `docs/spec/scheduling/static_scheduler_semantics.md` + `docs/design/static_scheduler_design.md` | spec/design 분리 후 merge | 보류 |
| `docs/tile_based/spec/scheduling/prefill_decode_workload_mapping.md` | `docs/overview/dataflow_overview.md`(LLM 섹션) + `docs/spec/architecture/`(KV/Decode 규범) | split+merge | 보류 |
| `docs/tile_based/spec/ir/npu_ir_core_spec.md` | (메인 IR을 대체하지 않음) → `docs/process/archive/` 또는 `docs/design/` 참고 문서 | keep-as-reference 또는 archive | 보류 |
| `docs/tile_based/spec/ir/npu_ir_lowering_and_execution.md` | `docs/design/cmdq_generator_design.md` / `docs/design/static_scheduler_design.md` 보강 | split+merge | 보류 |
| `docs/tile_based/spec/ir/tile_ir_spec.md` | `docs/spec/ir/` 내 “옵션 스펙”으로 신규 `tile_ir_optional_spec.md` | move + 메인 IR에서 옵션 링크 | 보류 |
| `docs/tile_based/design/analysis/tile_rt_analysis_for_npu_simulator.md` | `docs/design/` 내 참고 문서(예: `docs/design/tile_rt_analysis.md`) | move | 보류 |
| `docs/tile_based/test/examples/pytorchsim_npu_ir_examples.md` | `docs/test/examples/pytorchsim_npu_ir_examples.md` | move + tile_based에 스텁/링크 | 완료 |
| `docs/tile_based/test/examples/tutorial_minimal_llama_to_tile_npu.md` | `docs/test/examples/tutorial_minimal_llama_to_tile_npu.md` | move + tile_based에 스텁/링크 | 완료 |
| `docs/tile_based/README.md` | 최종적으로 `docs/README_SPEC.md`에 통합 후 제거 | merge then delete | 보류 |

---

## 2) 순차 진행 규칙(권고)

1. “충돌 적고 독립적인 문서”부터 이동(예제/체크리스트/인덱스).
2. 스펙 승격은 항상 “메인 스펙에 merge → tile_based는 링크/스텁” 순서로 진행.
3. 링크 정리 기준:
   - 메인 문서는 절대경로(`docs/...`) 링크 허용
   - tile_based 문서는 상대경로 링크 권장(리포 내부 이동에 강함)
