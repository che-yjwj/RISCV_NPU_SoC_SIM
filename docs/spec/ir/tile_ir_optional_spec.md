# Tile IR Optional Specification (TDG / TileDesc / Tile Ops)

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

## 1. 문서 목적

본 문서는 TileGraph 이후 단계에서 스케줄러/시뮬레이터 인터페이스를 명확히 하기 위한
**선택적(대안적) 표현(Optional IR)** 인 **Tile IR**의 최소 스펙을 정의한다.

- Tile IR은 하드웨어 RTL 계약도, ISA 인코딩도 아니다.
- 동시에, 시뮬레이터/스케줄러 관점에서는 “실행 가능한(op schema가 명확한)” IR이어야 한다.

## 2. 메인 스펙과의 관계(중요)

- 메인 IR 스펙(`docs/spec/ir/npu_ir_spec.md`)은 **Layer-level IR → TileGraph → CMDQ** 흐름을 단일 소스 오브 트루스로 한다.
- 본 Tile IR은 그 흐름을 대체하지 않으며, **TileGraph 이후(tiling/memory planning 이후)** 단계에서
  스케줄러/시뮬레이터의 입력을 별도 포맷으로 고정하고 싶은 경우에 한해 채택할 수 있다.
- 따라서 Tile IR의 채택 여부는 구현/실험 범위에 따라 결정되며, 메인 IR의 규범을 변경하지 않는다.

관련:
- 타일 의미론(SSoT): `docs/spec/architecture/tile_semantics_spec.md`
- HW–SW 경계 계약: `docs/spec/architecture/tile_contract_spec.md`
- 정적 스케줄 의미론: `docs/spec/scheduling/static_scheduler_semantics_spec.md`

## 3. Tile IR의 위치

```text
ONNX / PyTorch
  ↓
Graph Normalize & Fusion
  ↓
Tiling & Memory Planning
  ↓
Tile IR  (this spec, optional)
  ↓
Lowering (TE / VE / DMA descriptors, static schedule)
  ↓
Simulator (TLS / Global-cycle)
```

## 4. 설계 원칙

1. 모든 연산은 Tile 단위로 표현된다.
2. 메모리 이동은 명시적이다. (DMA/전송 노드)
3. 동기화/의존성은 명시적이다. (pred/succ 또는 tag/wait로 표현)
4. Tile IR은 **명령어 나열이 아니라 실행 DAG**이다.
5. IR은 백엔드 독립적이며, 인코딩/마이크로아키텍처를 포함하지 않는다.

주의:
- Tile IR은 “virtual ISA처럼 보일 수 있는” op schema를 갖지만, 실제 ISA 포맷/마이크로옵은 다루지 않는다.

## 5. 실행 모델(Temporal Semantics)

Tile IR은 정적 스케줄링 기반 실행을 전제로 한다.

- (권고) 코어별 실행 스트림은 정적으로 결정된다.
- Compute(TE/VE) 실행은 deterministic latency를 가정할 수 있다. (TLS)
- Data movement(DMA)는 Compute와 중첩될 수 있으나, 자원/큐 깊이/대역폭 제약으로 stall이 발생할 수 있다.

## 6. 메모리 모델

### 6.1 메모리 공간

- DRAM: 오프칩, 입력/출력/KV-cache 영속 저장, 명시적 DMA로만 접근
- SPM: 온칩 소프트웨어 관리 메모리, Tile payload의 기본 상주 공간
- 엔진 로컬 버퍼(TE/VE local): IR 관점에서 비가시적(주소화되지 않음), 구현 세부 영역

### 6.2 Residency 규칙

- Compute Tile은 입력/출력이 SPM에 resident일 때만 실행 가능하다.
- Residency lifetime(언제 load하고 언제 free할지)은 스케줄러/로어링 결과에 의해 결정된다.

## 7. TileDesc 핵심 구조

Tile IR의 기본 노드는 TileDesc이며, TDG의 노드가 된다.

```text
TileDesc {
  tile_id: uint32
  tile_kind: enum { COMPUTE, VECTOR, DMA, CONTROL }
  op: enum { GEMM_T, SOFTMAX_T, LNORM_T, LOAD_TILE, STORE_TILE, ... }

  inputs:  TileRef[]   # tiles in SPM (or DRAM for DMA source)
  outputs: TileRef[]   # tiles in SPM (or DRAM for DMA dest)

  deps:
    pred_tiles[]       # must complete before this tile can issue

  resource_hint:
    preferred_engine: { TE | VE | DMA }
    exclusive: bool

  latency_hint:
    est_cycles: optional[int]   # TLS용 힌트 (고정 강제 아님)
}
```

## 8. Tile Dependency Graph (TDG)

Tile IR은 암묵적 순서를 갖지 않으며, TDG로만 실행 순서를 결정한다.

```text
LOAD A ─┐
        ├─ GEMM ─→ LNORM ─→ STORE
LOAD B ─┘
```

TDG는 다음에 사용된다.

- Static Scheduler (우선순위/자원 제약/결정성)
- Timeline / Gantt 시각화
- 병목(utilization, stall) 분석

## 9. Tile Ops (Core Op Schema)

아래는 Tile IR이 제공해야 하는 최소 op schema 예시이다.

### 9.1 Compute / Vector Ops

```text
GEMM_T(A_tile, B_tile) -> C_tile
VEC_ADD_T(A_tile, B_tile) -> C_tile
LNORM_T(X_tile, gamma, beta) -> Y_tile
SOFTMAX_T(X_tile) -> Y_tile
```

### 9.2 Memory Ops (DMA)

```text
LOAD_TILE(DRAM_addr)  -> Tile(SPM)
STORE_TILE(Tile(SPM)) -> DRAM_addr
```

- LOAD/STORE는 Tile 단위로만 수행된다.
- DRAM 접근은 Memory Op로만 허용된다.

### 9.3 Synchronization

```text
WAIT_TILE(tile_id)
BARRIER(tile_group)
```

동기화의 구체 모델(예: tag/wait)은 메인 스펙의 선택/확장에 따라 달라질 수 있다.

## 10. 불변성 & 확장성

Tile IR에서 변할 수 있는 것과, 변하면 안 되는 것을 분리한다.

| 변경 가능 요소(설정/프로파일) | 불변 요소(스펙) |
|---|---|
| Tile size/shape(세대별) | Tile op 의미론 |
| TE/VE latency 파라미터 | 명시적 dependency |
| DMA/NoC/DRAM BW | 명시적 memory ops |
| 스케줄 우선순위 정책 | TDG 기반 실행 |

## 11. Summary

- Tile IR은 TDG 기반 실행 스펙이며, Tile op schema를 포함한다.
- Compute는 SPM resident 타일을 입력/출력으로 사용한다.
- DRAM 접근은 DMA(memory op)로만 표현된다.
- 인코딩/RTL은 별도 계층(Descriptor/CMDQ/ISA)에서 다룬다.

