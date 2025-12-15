# Static Scheduler Semantics Specification

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 목적

본 문서는 TileGraph/TDG 기반 Offline Compiler의 **정적 스케줄(Static Schedule)** 이 만족해야 하는
최소 의미론(semantics)을 정의한다.

이 스펙은 알고리즘(heuristic)이나 구현 구조를 강제하지 않는다.
대신 “올바른 스케줄”의 불변 규칙(의존성/ID/결정론/메모리 경계)을 고정한다.

관련 문서:
- 타일 의미론: `docs/spec/architecture/tile_semantics_spec.md`
- HW–SW 경계 계약: `docs/spec/architecture/tile_contract_spec.md`
- CMDQ 포맷: `docs/spec/isa/cmdq_format_spec.md`
- Cycle loop 결정론: `docs/design/cycle_loop_design.md`
- 경합 모델: `docs/spec/timing/bus_and_noc_model.md`, `docs/spec/timing/spm_model_spec.md`

## 2. 입력/출력 정의

### 2.1 입력

정적 스케줄러는 최소한 아래 정보를 입력으로 받는다.

- **TDG(Tile Dependency Graph)**: tile-level DAG (암묵적 순서 없음)
- **SPM allocation 결과**: tile별 bank/offset 및 용량 제약 정보(필요 시)
- **HW 구성**: `N_dma`, `N_te`, `N_ve` 및 타이밍/경합 정책 식별자(프로파일)

### 2.2 출력

스케줄러 출력은 아래 중 하나(또는 동등한 표현)로 관측 가능해야 한다.

- **ScheduleDAG**: entry 목록 + `deps_before`(선행 완료 조건) 관계
- 또는 **CMDQ**: 스케줄이 flatten된 실행 큐(`docs/spec/isa/cmdq_format_spec.md`)

스케줄 결과는 trace로 재현/검증 가능해야 한다.

## 3. 불변 규칙(필수)

### 3.1 의존성 보존

- 스케줄은 TDG의 의존성을 보존해야 한다.
- 어떤 entry도 자신이 의존하는 predecessor가 완료되기 전에 issue/실행될 수 없다.

### 3.2 타일 라이프사이클/메모리 규칙 준수

스케줄은 `docs/spec/architecture/tile_semantics_spec.md`의 불변식을 위반할 수 없다.

특히:
- tile payload는 SPM에 존재해야 하며, 엔진 간 공유는 SPM을 통해서만 발생한다.
- DRAM을 엔진 간 중간 결과 전달 경로로 사용하지 않는다.
- TE→VE 전달은 최소 1회 STB semantics(디스크립터 handoff)를 거친다.

### 3.3 엔진 귀속 및 ID 유효 범위

- 각 entry는 정확히 하나의 `engine_type`(DMA/TE/VE)에 귀속되어야 한다.
- `dma_id`, `te_id`, `ve_id`는 구성의 유효 범위 내여야 한다.
  - 유효 범위/기록은 `docs/spec/isa/cmdq_format_spec.md` 및 trace의 `config_snapshot` 정의를 따른다.

### 3.4 결정론(Determinism)

동일한 입력(TDG + 동일 HW 구성/정책 + 동일 초기 상태)이라면 스케줄 결과는 항상 동일해야 한다.

- 랜덤/RNG/seed 기반 tie-break는 금지한다.
- 동일 조건에서의 엔진 배정/entry ordering은 고정 규칙으로 정의되어야 한다.
  - 예: `(engine_type_order, engine_id, entry_id)` 기반 안정 정렬.

### 3.5 관측 가능성(Traceability)

스케줄 결과로부터 최소한 아래가 역추적 가능해야 한다.

- entry ↔ 원천 TDG/tile 식별자 매핑
- entry의 `deps_before` 관계
- entry의 `engine_type` 및 `*_id`

## 4. 권고 규칙(비규범)

아래 항목은 구현 선택이지만, trace/분석 품질을 위해 권고한다.

- stall reason 분류(엔진 busy / SPM capacity / SPM bank conflict / bus contention 등)
- Prefill/Decode 구분을 trace phase로 기록(LLM 워크로드 분석 용이)
- KV cache 트래픽을 별도 role로 표기(예: kv_bytes)

## 5. 참고(설계/예시 트랙)

- 알고리즘/휴리스틱/구현 예시: `docs/design/static_scheduler_design.md`
