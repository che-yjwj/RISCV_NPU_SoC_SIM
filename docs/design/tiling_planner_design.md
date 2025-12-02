# Tiling Planner Design
**Path:** `docs/design/tiling_planner_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
TilingPlanner는 Annotated NPU IR과 하드웨어/메모리 제약을 기반으로 **LayerIR를 tile 단위 연산(Tiles)으로 분해**하여 TileGraph를 구성한다.  
이 문서는 타일 크기 결정 기준, TileGraph 구조, 타일 의존성 모델을 정의한다.

관련 스펙:
- `docs/spec/ir/npu_ir_spec.md`
- `docs/spec/ir/tensor_metadata_spec.md`
- `docs/spec/quantization/bitwidth_memory_mapping.md`

## 2. 책임
- **입력**
  - Quantization annotation이 적용된 NPU IR.
  - 하드웨어 파라미터: SPM 용량, 엔진 개수, bank 수, alignment 등.
- **출력**
  - TileGraph: tile 노드, tile 간 데이터 의존성 edges.
  - 각 tile에 대한 shape 정보 (예: GEMM: M_tile, N_tile, K_tile).
- **주요 역할**
  - 레이어별로 tile 크기를 결정하여 SPM/엔진 제약을 만족시키면서 병렬성을 최대화.
  - tile 간 producer/consumer 관계를 그래프로 표현.
- **하지 말아야 할 일**
  - 실제 SPM bank/offset 배정 (SPMAllocator 책임).
  - 엔진 스케줄링(CMDQ 순서 결정).

## 3. 내부 구조

### 3.1 TileGraph 구조
```python
class TileNode:
    id: str
    parent_layer_id: str
    op_type: str
    tile_shape: dict   # e.g., {\"M\": 64, \"N\": 128, \"K\": 256}
    role: str          # compute / load / store / kv_update 등 (선택)
    qbits: dict        # {\"w\": 4, \"a\": 8, \"kv\": 4} (필요 시)
```

- `TileGraph`:
  - `nodes: list[TileNode]`
  - `edges: list[(producer_tile_id, consumer_tile_id)]`

### 3.2 서브 컴포넌트
- `TileShapePlanner`:
  - 레이어별 tile shape 후보 생성.
- `TileDependencyBuilder`:
  - tile 간 데이터 흐름에 따른 edge 생성.

## 4. 알고리즘 / 플로우

### 4.1 GEMM 타일링 예시
1. LayerIR에서 `M, N, K`와 tensor qbits/bytes를 읽는다.
2. candidate tile 크기 집합에서 SPM 용량을 초과하지 않는 후보를 선택:
   ```text
   bytes_ifm_tile + bytes_wgt_tile + bytes_ofm_tile <= spm_capacity_per_engine
   ```
3. 병렬성(TE 수)과 alignment를 고려하여 `M_tile`, `N_tile`, `K_tile` 결정.
4. 각 tile에 대해 TileNode 생성, partial sum이 필요한 경우 의존성 edge 추가.

### 4.2 LLM(Attention) 타일링 예시
- Q/K/V projection:
  - head, seq dimension 기준으로 타일 분할.
- KV cache:
  - seq 방향(tile per token or group of tokens).
- TileGraph에서 head/seq 축을 명시적으로 표현해 StaticScheduler에서 head parallelism을 이용할 수 있게 한다.

### 4.3 타일링 전략 요약 표 (1D/2D/Attention)

| Layer 유형 | 기본 축 | 타일링 축 | 전략 요약 |
| --- | --- | --- | --- |
| GEMM/FFN | (M, N, K) | M, N | SPM 용량 내에서 `M_tile×N_tile`를 크게 잡고, K는 가능한 한 크게 유지해 compute 효율 극대화 |
| Conv (2D) | (N, H, W, C) | H, W, C | SPM에 IFM/WGT/OFM가 동시에 들어가도록 H/W를 우선 타일링, C는 channel grouping에 맞춰 분할 |
| LayerNorm/RMSNorm | (B, T, H) | H | hidden size(H)를 lane 수에 맞춰 타일링, 토큰 단위(B×T)는 VE 병렬성으로 처리 |
| Attention (Q/K/V) | (B, T, H, D) or (B, H, T, D) | T, H | KV cache는 T(시퀀스) 기준으로 타일링, 다중 head(H)는 가능한 병렬로 유지 |
| KV Cache Update | (B, H, T, D) | T | 새 토큰 또는 토큰 블록 단위로 T를 타일링하여 append/copy 비용 최소화 |

> 실제 구현에서는 위 전략을 기본값으로 두되, auto-tuning이나 workload 특성에 따라 축/크기를 조정할 수 있다.

## 5. 인터페이스
- `TilingPlanner.plan(ir: NpuIr, hw_config) -> TileGraph`

구성 파라미터:
- max tile size per dimension.
- 우선 기준 (latency vs memory footprint vs parallelism).

## 6. 예시 시나리오
- 단일 GEMM 레이어에 대해:
  - 다양한 tile 크기 후보를 비교하여  
    SPM 용량과 TE 개수 제약을 만족하는 타일링이 만들어지는지 확인.

## 7. 향후 확장
- auto-tuning tile search (latency 모델을 사용해 후보 평가).
- heterogenous tile support (레이어별 다른 정책).
