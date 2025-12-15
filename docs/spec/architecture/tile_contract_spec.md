# Tile Contract Specification (HW–SW Boundary)

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 목적

본 문서는 타일 기반 NPU 모델에서 **HW–SW 경계 계약(Contract)** 을 정의한다.
컴파일러/런타임/시뮬레이터/하드웨어 모델이 공통으로 준수해야 하는 “최소 규범”을 고정한다.

이 문서는 타일 의미론(라이프사이클/메모리/TE–VE handoff)을 정의하는 `tile_semantics_spec.md`를 보완한다.

관련 문서:
- 타일 의미론(SSoT): `tile_semantics_spec.md`
- STB 채택 RFC: `stb_adoption_rfc.md`
- KV cache 의미론(LLM): `kv_cache_semantics_spec.md`
- CMDQ 포맷/필드: `docs/spec/isa/cmdq_format_spec.md`
- Opcode 정의: `docs/spec/isa/opcode_set_definition.md`
- 결정론적 경합 모델: `docs/spec/timing/bus_and_noc_model.md`, `docs/spec/timing/spm_model_spec.md`

## 2. 범위(Scope)

본 계약이 고정하는 것:
- Tile이 “데이터 이동/스케줄링/연산”의 최소 단위라는 점
- SPM/STB/DRAM 책임 경계(중간 결과 전달 경로 포함)
- 엔진(DMA/TE/VE) 관점의 **원자성(atomicity)**, 순서, 관측 가능성(trace)
- 결정론적 실행(동일 입력이면 동일 결과) 관점에서 필요한 식별자/규칙

본 계약이 고정하지 않는 것:
- 특정 수치(예: TE 타일의 M/N/K 크기, VE vector length, DMA burst size)  
  → 이는 “프로파일/구성(config)”의 영역이며, 관련 스펙에서 요구 시 별도 고정한다.

## 3. Tile 최소 계약

- Tile은 스케줄러/시뮬레이터/트레이스에서 **식별 가능해야 한다**(예: `tile_id`).
- Tile payload는 **SPM에만** 존재하며, 엔진 간 공유는 SPM을 통해서만 일어난다.
- 엔진 간 handoff는 payload 이동이 아니라 **디스크립터(메타데이터) handoff**로 표현된다(STB semantics).

## 4. 메모리/전달 계약

### 4.1 DRAM

- DRAM은 입력/최종 출력/KV cache 같은 영속 데이터에 한해 사용된다.
- 금지: DRAM을 엔진 간 중간 결과 타일 전달 경로로 사용하는 것.

### 4.2 SPM

- SPM은 타일 payload의 유일한 공유 저장소이며, 모든 엔진은 SPM을 통해 타일을 주고받는다.
- 타일 allocate/free는 컴파일러/스케줄러가 명시적으로 제어하며, trace로 관측 가능해야 한다.

### 4.3 STB(Shared Tile Buffer)

- STB는 타일 payload 저장소가 아니라, **디스크립터 handoff 경계(semantic construct)** 이다.
- STB를 payload 버퍼처럼 사용(복사/저장/전달)하는 구조는 금지된다.

## 5. 엔진 계약(DMA/TE/VE)

### 5.1 DMA

- DMA 명령은 DRAM↔SPM 이동을 표현하며, 최소 단위는 “타일”로 취급된다.
- DMA ordering은 CMDQ에서 명시적으로 정의되어야 하며(의존성/순서), 실행 결과는 결정론적이어야 한다.
- DMA 엔진/채널 수 `N_dma` 및 `dma_id` 유효 범위는 `docs/spec/isa/cmdq_format_spec.md` 및 trace의 `config_snapshot` 정의를 따른다.

### 5.2 TE / VE

- TE/VE 명령은 SPM에 있는 tile payload를 입력으로 소비하고, 결과를 SPM에 기록한다.
- TE→VE 전달은 최소 1회 STB semantics(디스크립터 handoff)를 거친다. (payload는 여전히 SPM에 존재)
- TE/VE의 연산 지원 범위(가능한 opcode/형상/데이터 타입)는 `docs/spec/isa/opcode_set_definition.md`를 따른다.

### 5.3 원자성(Atomicity)과 선점

- 기본 계약: 하나의 엔진 명령(예: `TE_*_TILE`, `VE_*_TILE`)은 타일 단위로 **원자적**으로 실행된다.
  - 실행 중간에 동일 타일이 다른 엔진에 의해 관측/소비되는 것은 금지된다.
- 만약 구현이 tile-level preemption/partial write를 지원한다면,
  그 의미론(관측/복구/trace)이 별도 스펙으로 고정되어야 한다(기본 계약 범위 밖).

## 6. 결정론(Determinism) 요구사항

동일한 입력(CMDQ + 동일 config + 동일 초기 메모리 상태)에 대해 시뮬레이터는 항상 동일한 결과를 내야 한다.

- Bus/NoC/SPM 경합은 global cycle 기반으로 모델링하되, arbitration/tie-break는 고정 규칙을 사용한다.
- 엔진 식별자(`dma_id`, `te_id`, `ve_id`)는 tie-break 키 구성에 사용될 수 있어야 한다.
- 상세 규칙은 `docs/spec/timing/bus_and_noc_model.md`, `docs/spec/timing/spm_model_spec.md`를 따른다.

## 7. 금지 패턴(요약)

- DRAM을 중간 결과 전달 경로로 사용
- STB를 payload 저장소로 사용
- SPM을 캐시처럼 자동 eviction/암묵적 이동 대상으로 취급
- 엔진 명령이 타일을 부분적으로 쓰고 외부에서 관측 가능한 상태를 만들기(별도 스펙 없는 한)

## 8. 참고(통합 이력)

통합 이력은 `docs/process/tile_based_integration_mapping.md`를 참고한다.
