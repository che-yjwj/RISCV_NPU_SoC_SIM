# KV Cache Semantics Specification (Tiling / Residency / Reuse)

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 목적

본 문서는 타일 기반 실행 모델에서 LLM용 **KV cache**를 다룰 때,
Prefill/Decode 단계 모두에 대해 **허용되는 타일링/상주/재사용 구조**를 정의한다.

본 문서는 구현 트릭(최적화 기법)이나 특정 수치(프리패치 깊이 등)를 고정하지 않으며,
아래 “규범(minimum invariants)”을 고정하는 것을 목표로 한다.

- KV cache의 DRAM 영속(residency) 및 append/update 의미론
- Decode 단계에서의 **Time 기반 타일링** 및 streaming 소비 규칙
- MQA/GQA에서의 **재사용 가능 범위**와 금지 패턴
- STB/TE/VE/메모리 계층과의 책임 경계

관련 문서:
- 타일 의미론(SSoT): `tile_semantics_spec.md`
- CMDQ/Opcode: `docs/spec/isa/cmdq_format_spec.md`, `docs/spec/isa/opcode_set_definition.md`
- Trace 체크리스트: `docs/spec/trace/tile_semantics_validation_checklist.md`
- KV 양자화(비트폭/traffic): `docs/spec/quantization/kv_cache_quantization_spec.md`

## 2. 용어

- **KV cache**: Prefill에서 생성되어 Decode에서 반복 소비되는 장기 입력 데이터(K/V).
- **Time dimension(T)**: 토큰 시간 축(Decode 단계에서 누적 증가).
- **Time_tile**: 연속된 시간 구간 `[t0, t1)`에 대한 KV cache 조각.
- **Dh**: head hidden dimension.
- **MQA**: Multi-Query Attention. 여러 Query head가 동일한 K/V를 공유.
- **GQA**: Grouped Query Attention. Query head를 group으로 묶고 group별 K/V를 공유.
- **SPM**: 온칩 scratchpad. 타일 payload의 유일한 공유 저장소.
- **STB semantics**: 엔진 간 **디스크립터** handoff 경계. payload 저장소가 아니다.

## 3. KV cache의 기본 불변식

1) **DRAM 영속**: KV cache의 장기 저장소는 DRAM이며, Prefill/Decode 전 구간에서 일관되어야 한다.  
2) **입력 데이터**: KV cache는 (Decode 관점에서) 연산 결과 전달물이 아니라 **연산 입력 데이터**이다.  
3) **SPM staging**: Decode에서 KV cache는 필요 범위만 Time_tile 단위로 DRAM→SPM staging되어 소비된다.  
4) **STB 경유 금지**: KV cache payload는 STB를 통해 전달/버퍼링되어서는 안 된다. (STB는 TE→VE 결과 디스크립터 handoff 전용)  
5) **전체 상주 금지**: KV cache 전체를 SPM에 상주시키는 구조는 허용되지 않는다.

## 4. Time 기반 타일링 규칙(Decode)

Decode 단계에서 KV cache는 Time dimension을 1차 기준으로 타일링되어야 한다.

- **연속성**: 한 Time_tile은 반드시 **연속된 시간 구간**이어야 한다.
- **단계 내 streaming 소비**: 한 Decode step(=token 처리)에서 KV cache는 Time_tile 스트림으로 소비될 수 있으며,
  소비가 끝난 Time_tile은 SPM에서 해제될 수 있다(다음 step에서 재로드 가능).
- **무작위 접근 금지**: Time dimension을 무시한 임의 접근/불규칙 순회는 허용되지 않는다.

## 5. 재사용 규칙(MQA/GQA)

재사용은 “DRAM 재로드 회피”를 위해 **SPM 상주 상태**에서만 허용된다.

### 5.1 MQA

MQA에서는 하나의 KV tile이 다수 Query head에 의해 공유된다.

- KV cache는 Query head 차원을 기준으로 복제/분할하여 저장하지 않는다.
- 동일 Time_tile의 K/V는 **SPM에 한 번 staging된 뒤** 여러 Query head에서 재사용될 수 있다.
- 금지: Query head마다 동일 Time_tile을 중복 로드하거나 중복 저장하는 구조.

### 5.2 GQA

GQA에서는 group 경계가 구조적으로 고정된다.

- KV cache는 group 단위로 분리되어야 한다.
- 재사용은 **동일 group + 동일 Time_tile** 범위에서만 허용된다.
- 금지: group 경계를 무시한 flatten, group 간 KV 공유/재사용.

## 6. (선택) Interleaved Heads/Groups 레이아웃 제약

메모리 효율(예: DRAM burst 효율, SPM bank conflict 완화)을 위해 head/group 차원을 interleave 배치할 수 있다.
단, 아래 제약을 위반해서는 안 된다.

- Time_tile 경계를 넘는 interleaving 금지
- (GQA) group 경계를 넘는 interleaving 금지
- Prefill/Decode 간 레이아웃 불일치 금지(동일 run에서의 구조적 일관성)

구체적 stride/정렬/권고값은 구현/프로파일에 따라 달라질 수 있으며, 본 문서의 범위를 벗어난다.

## 7. CMDQ/시뮬레이터 최소 요구사항

- KV cache에 대한 DRAM↔SPM 이동은 CMDQ에서 명시적으로 표현되어야 한다(예: `KV_LOAD_TILE`, `KV_STORE_TILE`).
- KV cache load/store 트래픽은 bus/NoC/SPM 경합 모델의 입력이 되며, 같은 입력이면 항상 같은 결과가 나오도록 **결정론적 중재**를 따른다.
  - 세부 규칙: `docs/spec/timing/bus_and_noc_model.md`, `docs/spec/timing/spm_model_spec.md`

## 8. 금지 패턴(요약)

- KV cache 전체를 SPM에 상주시키는 구조
- KV cache payload를 STB로 전달/버퍼링하는 구조
- Time dimension 기반 타일링을 무시한 임의 접근/순회
- (MQA/GQA) 공유 구조를 무시한 head별 KV 복제/중복 로드
- Prefill/Decode에서 서로 다른 논리 레이아웃을 사용(동일 run 기준)

## 9. 참고(Design)

- `docs/design/tile_rt_analysis.md`
