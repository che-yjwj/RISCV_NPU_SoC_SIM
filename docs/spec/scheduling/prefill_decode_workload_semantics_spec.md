# Prefill/Decode Workload Mapping Semantics Specification

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 목적

본 문서는 LLM 추론의 **Prefill/Decode** 두 단계가
동일한 타일 기반 실행 모델 위에서 어떻게 매핑되어야 하는지에 대한
최소 의미론(semantics)을 정의한다.

이 문서는 구현 알고리즘(스케줄 휴리스틱)이나 권고 파라미터(프리패치 깊이 등)를 고정하지 않는다.
대신 “허용되는 구조/금지되는 구조”와 관측 가능 조건을 고정한다.

관련 문서:
- 타일 의미론(SSoT): `docs/spec/architecture/tile_semantics_spec.md`
- KV cache 의미론(SSoT): `docs/spec/architecture/kv_cache_semantics_spec.md`
- 정적 스케줄 의미론: `docs/spec/scheduling/static_scheduler_semantics_spec.md`
- CMDQ/Opcode: `docs/spec/isa/cmdq_format_spec.md`, `docs/spec/isa/opcode_set_definition.md`

## 2. 용어

- **Prefill**: 긴 입력 시퀀스를 한 번에 처리하여 KV cache를 “생성/append”하는 단계(throughput 중심).
- **Decode**: 토큰 1개를 반복 처리하며 KV cache를 “반복 load + append”하는 단계(latency 중심).
- **Score tile**: `Q @ K^T`의 결과(Softmax 입력).
- **SPM**: 온칩 scratchpad.

## 3. 공통 불변식

1) **Tile 단위 표현**: Prefill/Decode 모두에서 연산/이동/스케줄의 최소 단위는 tile이다.  
2) **중간 결과 DRAM 전달 금지**: score/P 등 엔진 간 중간 결과를 DRAM에 저장해 전달 경로로 사용하지 않는다.  
3) **TE→VE handoff 규칙**: TE가 생성한 score tile은 최소 1회 STB semantics(디스크립터 handoff)를 거쳐 VE에서 소비된다.  
4) **결정론**: 동일 입력이면 항상 동일 결과(스케줄/타이밍/trace)가 나오도록 랜덤 기반 tie-break를 금지한다.

## 4. Prefill 매핑 의미론(필수)

Prefill 단계에서:

- Q/K/V projection 결과 중 **K/V는 DRAM의 KV cache로 저장(append/write-back)** 될 수 있다.
- Score tile 및 Softmax 결과(P)는 **DRAM으로 저장해서는 안 된다.**
  - score/P는 SPM에 상주한 상태로 TE↔VE 경계(STB semantics)를 통해 파이프라인으로 소비되어야 한다.
- 스케줄은 score 생성(TE)과 softmax 소비(VE)가 근접하도록 구성될 수 있으나, 이는 성능 최적화 영역이며 본 스펙은 강제하지 않는다.

## 5. Decode 매핑 의미론(필수)

Decode 단계에서:

- `K_new/V_new`는 **DRAM의 KV cache에 append** 되어야 한다.
- 과거 KV cache(`K_cache/V_cache`)는 **DRAM→SPM으로 필요한 범위만 Time_tile 단위로 staging** 되어 소비된다.
  - Time 기반 타일링/재사용 금지 규칙은 `docs/spec/architecture/kv_cache_semantics_spec.md`를 따른다.
- Score tile은 `Q(1) × K(T)` 형태의 streaming 소비로 생성될 수 있으며, Softmax는 필요 시 multi-pass reduction으로 구현될 수 있다.
  - 어떤 경우에도 score tile은 DRAM으로 우회해서 전달되지 않는다.

## 6. 관측 가능성(Trace/검증)

시뮬레이터/트레이스는 Prefill/Decode를 최소한 아래 관점에서 구분 가능해야 한다.

- phase 구분(예: `PREFILL`, `DECODE`) 또는 동등한 메타데이터
- KV cache load/store 트래픽이 식별 가능(예: role=`kv`, 또는 별도 채널)
- TE/VE/DMA 엔트리의 `*_id`, `deps_before` 기반의 실행 순서 재현 가능

## 7. 참고(통합 이력)

통합 이력은 `docs/process/tile_based_integration_mapping.md`를 참고한다.
