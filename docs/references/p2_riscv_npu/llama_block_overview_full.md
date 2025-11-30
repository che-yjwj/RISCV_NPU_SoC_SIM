
# LLaMA Block Overview — IA_RISC_V_NPU_Simulator v2  
**Full Technical Example Document (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team

---

# 0. Purpose

본 문서는 LLaMA 스타일 Transformer **1 block**을  
IA_RISC_V_NPU_Simulator v2 시점에서 **타일 관점 / 스케줄러 관점 / ISA 흐름 관점**에서  
체계적으로 이해할 수 있도록 구성된 **개념·구조·데이터흐름 오버뷰 문서**이다.

이 문서는 다음 관점을 모두 포괄한다:

- LLaMA block 내부 연산 구조(QKV projection, Attention, FFN)  
- KV-cache 생성 및 사용 흐름  
- 모델 텐서 차원 설명  
- 타일 단위 분해 결과(tiling map 예시)  
- 타일 그래프(TileOpGraph) 수준의 오퍼레이터 의존성  
- TE/VE/DMA/NPU-ISA 전개와의 대응 관계  
- 디코딩 모드(autoregressive)에서의 timestep별 동작  
- NPU-friendly 구조로 재해석된 block-level architecture  

실제 end-to-end ISA 예시는 별도 문서에서 다루며,  
본 문서는 전체적인 “LLaMA block을 어떻게 시뮬레이터에서 이해하는가”를 설명하는 역할을 한다.

---

# 1. LLaMA Block Computation Overview

LLaMA block은 크게 다음 세 부분으로 구성된다:

1. **Self-Attention Sub-layer**  
   - Q = X·Wq  
   - K = X·Wk  
   - V = X·Wv  
   - KV-cache append  
   - Attention(Q,K,V) = Softmax(QKᵀ / √d) · V  
   - O = Attention(Q,K,V) · Wout

2. **FeedForward Network (FFN)**  
   - Hidden = GELU(X·W1 + b1)  
   - Y = Hidden·W2 + b2

3. **RMSNorm / LayerNorm**  
   - Norm before attention  
   - Norm before FFN

전체 구조:

```
X_norm = RMSNorm(X)

# Attention
Q = X_norm Wq
K = X_norm Wk
V = X_norm Wv
Store K_t, V_t → KV-cache
K_all, V_all ← KV-cache load
S = Softmax(Q K_allᵀ)
O = S V_all
AttnOut = O Wout

# FFN
FFN_in = RMSNorm(AttnOut)
FFN_hidden = GELU(FFN_in W1 + b1)
Y = FFN_hidden W2 + b2
```

---

# 2. Tensor Shapes in LLaMA

기본 차원 정의(예):

| Symbol | Meaning | Example |
|--------|---------|---------|
| B | Batch | 1 (decode) |
| S | Sequence length | grows with timestep |
| H | Hidden dim | 4096 |
| D | Head dim | 128 |
| NH | Num heads | 32 |
| SH | Num shards per head (tiling) | hardware-dependent |

### Q/K/V shape per head:
```
Q: [B, 1, NH, D]
K: [B, t, NH, D]
V: [B, t, NH, D]
```

---

# 3. Tile Decomposition (Example)

LLM block을 실제 NPU에서 처리하려면 모든 텐서를 타일로 나누어야 한다.

예시 타일 크기:
```
Tile_M = 64
Tile_K = 64
Tile_N = 64
```

예시 분해:

### Q projection tile
```
(M = 1, K = H) × (H, NH*D)
→ tile grid (1×64) × (64×32)
```

### KV-cache tile
KV-cache는 time × dim 축을 다음과 같이 나눈다:
```
K_all tile: (t_tile, D_tile)
V_all tile: (t_tile, D_tile)
```

---

# 4. TileOp Graph for LLaMA Block

LLaMA block의 연산을 타일 수준에서 그래프로 나타내면:

```
RMSNorm → Q_tile
        → K_tile
        → V_tile
Q_tile -----> QKᵀ_tile -----> Softmax_tile -----> Attn·V_tile -----> OutProj_tile
K_tile -----> KV_Store
V_tile -----> KV_Store
KV_Load(K_all_tile)
KV_Load(V_all_tile)
```

FFN 부분:

```
RMSNorm → MatMul(W1) → Bias → GELU → MatMul(W2) → Bias
```

이 그래프는 타일 간의 데이터 의존성을 명확하게 보여주며,  
스케줄러가 Compute/DMA concurrency를 최적화하는 데 사용된다.

---

# 5. KV-Cache in LLaMA Block

### KV-cache Layout per head

```
KVCache[head][timestep][D]
```

시뮬레이터 관점에서는 다음처럼 DRAM에서 관리된다:

| Region | Contents |
|--------|----------|
| Base + head_offset | K tiles for head |
| Base + head_offset + K_bytes | V tiles for head |

KV-store는 타일 단위 append:

```
K_t, V_t appended at timestep t
KV_STORE_TILE head, spmK, K, addr_k(t)
KV_STORE_TILE head, spmV, V, addr_v(t)
```

KV-load는 range descriptor 기반:

```
KV_LOAD_TILE spmKall, head, K, kv_range_ptr
KV_LOAD_TILE spmVall, head, V, kv_range_ptr
```

---

# 6. NPU-Level Architecture Usage

LLaMA block은 NPU에서 다음 유닛을 사용한다:

| Component | Role |
|----------|------|
| TE(MatMul/QKᵀ/AV) | MatMul-based ops |
| VE(GELU/Softmax/RMSNorm) | vector ops |
| DMA | DRAM↔SPM load/store |
| SPM | tile buffer |
| KV-engine (via KV ISA) | KV append/load |

Self-attention 전체는 TE + VE + DMA + KV ISA가 모두 관여하는 복합 파이프라인이다.

---

# 7. LLaMA Block — Top-Level Dataflow Diagram

```
     ┌──────────┐
     │ RMSNorm  │
     └─────┬────┘
     ┌─────┴───────────────┬───────────────────┬───────────────────┐
     │Wq projection         │Wk projection       │Wv projection       │
     └─────┬────────────────┴──────────┬─────────┴──────────┬───────┘
           │                           │                     │
           │                  ┌────────┴─────────┐           │
           │                  │ KV-store (K,V)   │           │
           │                  └────────┬─────────┘           │
           │                           │                     │
           │                  ┌────────┴─────────┐           │
           │                  │ KV-load(K_all,V_all)         │
           │                  └────────┬─────────┘           │
           │                           │                     │
      ┌────┴───────┐             ┌──────┴─────┐
      │  QKᵀ       │             │  Softmax    │
      └────┬───────┘             └─────┬──────┘
           │                           │
           └───────────────┬──────────┘
                           │
                        ┌──┴──────────┐
                        │  Attn·V     │
                        └────┬────────┘
                             │
                        ┌────┴──────────┐
                        │ Out projection │
                        └────┬──────────┘
                             │
                       ┌─────┴──────────┐
                       │     FFN        │
                       └────────────────┘
```

---

# 8. NPU Execution Ordering Example (Conceptual)

Self-attention 내부에서 타일 단위 스케줄링 개념 예시:

```
# Load X tiles
DMA_LOAD_TILE spmX, X_addr

# Q/K/V matmuls (interleaved with DMA of weights)
spmQ = MatMul(spmX, spmWq)
spmK = MatMul(spmX, spmWk)
spmV = MatMul(spmX, spmWv)

# KV-store
KV_STORE_TILE head, spmK
KV_STORE_TILE head, spmV

# Load past K/V
KV_LOAD_TILE spmKall
KV_LOAD_TILE spmVall

# QKᵀ
TE_QKT_TILE spmScore, spmQ, spmKall
VE_SOFTMAX_TILE spmScore
TE_AV_TILE spmO, spmScore, spmVall

# Output projection
spmY = MatMul(spmO, spmWout)

# FFN
spmFFN = MatMul(GELU(spmY), spmW1)
spmY2 = MatMul(spmFFN, spmW2)
```

---

# 9. LLaMA Block and Scheduler Interaction

Scheduler는 다음을 고려하여 타일 실행 순서를 결정한다:

- DMA load latency  
- TE compute latency  
- VE compute latency  
- KV-load stall 가능성  
- Multi-core TE 병렬성  
- SPM buffer lifetime  
- tile DAG topology  

시뮬레이터는 이를 timeline/Gantt chart로 시각화한다.

---

# 10. LLaMA Block in Decoding Mode

Autoregressive decoding에서는 timestep마다:

- Q/K/V projection → KV-store  
- t=0에서 KV-load는 trivial (K_all = K_t)  
- t>0에서는 KV-load 증가  
- Softmax length 증가  
- TE_QKT_TILE/TE_AV_TILE의 tile grid도 timestep에 따라 증가  

즉, timestep t마다 연산량이 증가하며, 시뮬레이터는 이를 정확히 반영해야 한다.

---

# 11. Summary of LLaMA Block Ops (Tile-Level)

| Stage | Tile Ops |
|--------|-----------|
| RMSNorm | VE_RMSNORM_TILE |
| Q/K/V | TE_MATMUL_TILE (3×) |
| KV-store | KV_STORE_TILE (2×) |
| KV-load | KV_LOAD_TILE (2×) |
| Attention Scores | TE_QKT_TILE |
| Softmax | VE_SOFTMAX_TILE |
| Attn·V | TE_AV_TILE |
| OutProj | TE_MATMUL_TILE |
| FFN | TE_MATMUL + VE_GELU + TE_MATMUL |

---

# End of Document
