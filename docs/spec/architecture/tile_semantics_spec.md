# Tile Semantics Specification (Lifecycle / Memory / TE–VE Dataflow)

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 목적

본 문서는 타일 기반 실행 모델에서 다음 “최소 불변 규칙(minimum invariants)”을 정의한다.

- 타일 라이프사이클(할당/생산/전달/소비/해제)의 합법/불법 조건
- 메모리 계층(DRAM/SPM/엔진 로컬)의 책임 경계
- TE–VE 데이터플로우(타일 payload vs 디스크립터 handoff)의 의미론

이 문서는 버스 프로토콜/핀/레지스터맵 같은 구현 세부 사항을 다루지 않는다.

관련 RFC:
- STB 채택 범위: `stb_adoption_rfc.md`
관련 스펙:
- KV cache 의미론(LLM): `kv_cache_semantics_spec.md`
- HW–SW 경계 계약: `tile_contract_spec.md`

## 2. 용어

- **Tile**: 스케줄링/데이터 이동/연산의 최소 단위
- **DRAM**: 오프칩 영속 저장소(입력/최종 출력/KV cache 등)
- **SPM(Scratchpad Memory)**: 온칩 소프트웨어 관리 메모리(타일 payload의 유일한 공유 저장소)
- **STB(Shared Tile Buffer)**: 타일 **디스크립터** handoff 경계(semantic construct). payload 저장소가 아니다.
- **TE**: Tensor Engine(2D 고밀도 연산)
- **VE**: Vector Engine(후처리/정규화/reduction 중심)

주의:
- 메인 스펙에서 SPM은 일부 문서에서 “Global SRAM”으로도 불릴 수 있으며, 동일 계층으로 취급한다.

## 3. 메모리 계층 책임

### 3.1 DRAM

DRAM은 다음 목적에 한해 사용된다.

- 입력 텐서의 영속 저장
- 최종 출력 텐서의 저장
- KV cache 등 장기 입력 데이터의 영속 저장

금지:
- 연산 중간 결과 타일을 DRAM에 저장하여 엔진 간 전달에 사용

### 3.2 SPM

SPM은 다음을 책임진다.

- 타일 payload의 저장/공유(엔진 간 재사용 포함)
- 타일 라이프사이클의 기준점(anchor)
- DMA/TE/VE의 주소 기반(load/store) 접근 대상

SPM은 캐시가 아니며 자동 eviction/일관성/coherence를 제공하지 않는다.

### 3.3 엔진 로컬 버퍼

- 엔진 내부 작업공간(scratch)이며 IR/아키텍처 관점에서 주소화되지 않는다.
- 로컬 버퍼의 데이터는 엔진 외부로 노출/재사용될 수 없다.

## 4. Tile 라이프사이클 불변식

각 타일은 (논리적으로) 아래 상태를 순차적으로 거친다.

```text
Allocated → Produced → Handed-off → Consumed → (Reused | Freed)
```

시간 관점 요약:

```text
Time ─────────────────────────────────────────────────────▶

[Allocate] → [Produced in SPM] → [Descriptor handoff(STB)] → [Consumed] → [Freed]
```

불변 규칙:

1) **할당 전 소비 금지**: Allocated 이전에 어떤 엔진도 타일을 소비할 수 없다.  
2) **생산 전 handoff 금지**: Produced 이전에 STB/descriptor handoff가 발생할 수 없다.  
3) **handoff 동안 SPM 상주**: STB가 참조 중인 타일은 SPM에 반드시 존재해야 하며 해제될 수 없다.  
4) **소비 중 해제 금지**: Consumed 중(또는 예정)인 타일은 해제될 수 없다.  
5) **명시적 해제**: 타일 해제는 스케줄러 관점에서 결정적이고 관측 가능해야 한다.

## 5. TE–VE 데이터플로우 의미론(STB semantics)

### 5.0 구조 다이어그램(요약)

```text
┌─────────────────────────────────────────────────────────────┐
│                          DRAM                               │
│                  (입력 / 최종 출력 / KV cache)               │
└───────────────▲───────────────────────────────▲────────────┘
                │ DMA                             │ DMA
                │                                 │
┌───────────────┴─────────────────────────────────┴────────────┐
│                        SPM (Scratchpad)                       │
│                                                                │
│  - tile payload의 유일한 공유 저장소                            │
│  - 타일 라이프사이클의 기준점(anchor)                           │
│                                                                │
└───────────────▲───────────────────────────────▲────────────┘
                │                               │
        Load/Store (MM)                 Load/Store (MM)
                │                               │
        ┌───────┴───────┐               ┌───────┴───────┐
        │  Tensor Engine │               │  Vector Engine│
        │      (TE)      │               │      (VE)     │
        └───────┬───────┘               └───────┬───────┘
                │   Tile Descriptor (handoff)    │
                ▼                                │
        ┌────────────────────────────────────────┘
        │        STB semantics boundary
        │      (descriptor only, no payload)
        └────────────────────────────────────────
```

### 5.1 payload vs descriptor 분리

- 타일 **payload 데이터**는 SPM에만 존재한다.
- 엔진 간 전달은 **타일 디스크립터**로 표현된다.

### 5.2 TE → VE handoff

TE가 결과 타일을 생성할 때:

1) 결과 payload는 SPM에 기록된다.
2) 결과 타일 디스크립터가 STB 의미론으로 handoff 된다.
3) VE는 디스크립터를 수신한 뒤, SPM에서 payload를 로드해 소비한다.

TE→VE 최초 소비는 **최소 1회 handoff 경계(STB semantics)** 를 거쳐야 한다.

### 5.3 back-pressure

소비자(VE)가 준비되지 않은 경우, handoff 경계에서 역압이 발생할 수 있다.
이 역압은 DRAM으로 전파되는 것이 아니라, 엔진 간 경계에서 국소적으로 모델링되어야 한다.

### 5.4 TE/VE 역할 경계(요약)

- TE: GEMM/MAC 중심의 2D 고밀도 연산, tile 생산자(producer) 성격이 강함
- VE: softmax/LN/reduction/activation 등 후처리 중심, tile 소비자(consumer) 성격이 강함
- 금지: TE에서 reduction 중심 연산을 수행하거나 VE에서 대규모 GEMM을 수행하는 구조(역할 혼합)

## 6. 금지 패턴(요약)

- DRAM을 엔진 간 중간 결과 전달 경로로 사용
- STB를 payload 저장소로 사용
- SPM을 캐시처럼 자동 eviction/암묵적 이동 대상으로 취급
- 엔진 로컬 버퍼 데이터를 외부에서 관측/재사용

## 7. 시뮬레이터/컴파일러 요구사항(최소)

- SPM 점유(바이트/타일 수), bank/port conflict는 `docs/spec/timing/spm_model_spec.md`에 따라 모델링
- 타일 allocate/free 및 상태 전이를 trace로 관측 가능하게 기록
- handoff 경계(=STB semantics)에서의 stall/back-pressure 원인을 분류 가능하게 기록
- Bus/NoC/SPM 경합은 global cycle 기반으로 모델링하되, **결정론적**이어야 한다
  - 랜덤/RNG/seed 기반 중재 금지
  - arbitration 및 tie-break 규칙은 `docs/spec/timing/bus_and_noc_model.md`, `docs/spec/timing/spm_model_spec.md`에 의해 고정

## 8. 관련 문서(참고)

- 메모리/NoC 요약: `docs/overview/memory_noc_overview.md`
- 스케줄링 의미론: `docs/spec/scheduling/static_scheduler_semantics_spec.md`
- Prefill/Decode 매핑 의미론: `docs/spec/scheduling/prefill_decode_workload_semantics_spec.md`
