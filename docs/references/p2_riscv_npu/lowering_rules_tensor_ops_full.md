
# Lowering Rules for Tensor Ops — IA_RISC_V_NPU_Simulator v2  
**Full Technical Design Document (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

본 문서는 IA_RISC_V_NPU_Simulator v2에서  
**Tensor 연산(MatMul, Conv2D, FFN, LayerNorm, GELU, Softmax 등)**을  
타일 기반 **xNPU ISA 스트림**으로 정밀하게 변환하는  
**Lowering Rule(정식 규칙)**을 정의한다.

Lowering 규칙은 다음을 보장해야 한다:

- 타일 단위 TE/VE 실행 가능성  
- SPM → DRAM 위치 일관성  
- Dependency DAG 보존  
- TE/VE/DMA/SYNC 명령어 조합의 정확성  
- DRAM burst alignment 및 타일별 주소 범위 일관성  
- LLM workload에서 MatMul/FFN 중심으로 정확한 시뮬레이션 가능

---

# 1. Lowering Overview

Frontend(IR) → Tiling → TileOpGraph(Scheduler) → ISA Lowering 의 흐름 중  
ISA Lowering은 다음을 수행한다:

1. TileOpNode 종류(MatMul/Conv/etc.) 확인  
2. 입력 tile, weight tile, output tile의 메타데이터 분석  
3. 필요한 DMA_LOAD, DMA_STORE 시퀀스 생성  
4. TE/VE compute tile 명령 생성  
5. fence(SYNC) 삽입  
6. core 배정에 따라 local ordering 생성  

ISA lowering 출력은 아래 형태:

```
[
  (opcode, dst, src0, src1, imm),
  ...
]
```

---

# 2. Common Lowering Patterns

모든 tensor ops는 다음 패턴을 공유한다:

```
1) Load input tiles from DRAM to SPM
2) (optional) Load weight tiles
3) Compute TE/VE tile
4) Store result tile to DRAM
5) SYNC to enforce dependency
```

---

# 3. MatMul Lowering (Core of LLM)

## 3.1 IR Signature

```
C = MatMul(A[M,K], B[K,N])
```

## 3.2 Tile decomposition (from Tiler)
A, B, C tile sets:

```
A(m, k), B(k, n) → C(m, n)
```

각 tile shape:

```
A_tile: (M_tile, K_tile)
B_tile: (K_tile, N_tile)
C_tile: (M_tile, N_tile)
```

---

## 3.3 MatMul Lowering Rule

Pseudo-code:

```
for each tile (m,n,k):
    DMA_LOAD_TILE spmA, A_dram_addr
    DMA_LOAD_TILE spmB, B_dram_addr
    SYNC_WAIT

    TE_MATMUL_TILE spmC, spmA, spmB

SYNC_WAIT
DMA_STORE_TILE spmC, C_dram_addr
```

---

## 3.4 Partial Sum Accumulation

MatMul은 K dimension에서 split될 수 있으므로:

```
if k_first:
    TE_MATMUL_TILE spmC = A*B
else:
    TE_MATMUL_TILE spmC += A*B   # accumulate
```

ACC-mode는 ISA 내 내부 flag로 처리.

---

# 4. Conv2D Lowering

## 4.1 IR Signature

```
Y[N, Cout, H, W] = Conv2D(X[N, Cin, H, W], W[Cout, Cin, KH, KW])
```

## 4.2 Tiling Axes

- Cout_tile  
- H_out_tile  
- W_out_tile  
- Cin partial tile (for SPM constraints)

---

## 4.3 Lowering Rule

```
for each tile (co, h, w, ci):
    DMA_LOAD_TILE spmX, X_tile_addr
    DMA_LOAD_TILE spmW, W_tile_addr
    SYNC_WAIT

    TE_MATMUL_TILE spmY, spmX, spmW     # im2col or direct conv

SYNC_WAIT
DMA_STORE_TILE spmY, Y_addr
```

Conv lowering은 MatMul 기반으로 구현되며,  
스케줄러는 im2col 또는 winograd 최적화 여부를 config로 전달할 수 있다.

---

# 5. FeedForward Network (FFN) Lowering

FFN consists of:

```
Hidden = GELU(X * W1 + b1)
Out    = Hidden * W2 + b2
```

## 5.1 Lowering for first MatMul + Bias + GELU

```
DMA_LOAD_TILE spmX, X_addr
DMA_LOAD_TILE spmW1, W1_addr
DMA_LOAD_TILE spmB1, B1_addr
SYNC_WAIT

TE_MATMUL_TILE spmH, spmX, spmW1
VE_ADD_TILE    spmH, spmH, spmB1
VE_GELU_TILE   spmH, spmH
```

---

## 5.2 Second MatMul

```
DMA_LOAD_TILE spmW2, W2_addr
SYNC_WAIT
TE_MATMUL_TILE spmO, spmH, spmW2
DMA_STORE_TILE spmO, O_addr
```

---

# 6. LayerNorm Lowering

Tile-level LN lowering:

```
DMA_LOAD_TILE spmX, X_addr
SYNC_WAIT
VE_RMSNORM_TILE spmY, spmX
DMA_STORE_TILE spmY, Y_addr
```

---

# 7. Softmax Lowering

```
DMA_LOAD_TILE spmScores, score_addr
SYNC_WAIT
VE_SOFTMAX_TILE spmScores, spmScores
DMA_STORE_TILE spmScores, score_addr_out
```

---

# 8. GELU Lowering

```
DMA_LOAD_TILE   spmX, X_addr
VE_GELU_TILE    spmX, spmX
DMA_STORE_TILE  spmX, out_addr
```

---

# 9. Bias Add Lowering

```
DMA_LOAD_TILE spmX, X_addr
DMA_LOAD_TILE spmB, B_addr
VE_ADD_TILE   spmX, spmX, spmB
DMA_STORE_TILE spmX, Y_addr
```

---

# 10. Mixed Ops: QKV Projection Lowering

```
DMA_LOAD_TILE spmX, X_addr

for Wq, Wk, Wv:
    DMA_LOAD_TILE spmW, W_addr
    TE_MATMUL_TILE spmOut, spmX, spmW
    DMA_STORE_TILE spmOut, Out_addr
```

---

# 11. Tiling-Aware Lowering Rules

### SPM Reuse

```
LOAD spmX once → reuse for 3 MatMuls
```

### KV-aware lowering

```
KV_STORE_TILE head_id, spmK, K, kv_addr
```

---

# 12. LLaMA Attention Lowering (Full Flow)

```
# QKV
TE_MATMUL_TILE spmQ, spmX, spmWq
TE_MATMUL_TILE spmK, spmX, spmWk
TE_MATMUL_TILE spmV, spmX, spmWv

# KV store
KV_STORE_TILE head, spmK, K, addr_k
KV_STORE_TILE head, spmV, V, addr_v

# KV load
KV_LOAD_TILE spmKall, head, K, kv_range
KV_LOAD_TILE spmVall, head, V, kv_range

# attention score
TE_QKT_TILE       spmS, spmQ, spmKall
VE_SOFTMAX_TILE   spmS, spmS
TE_AV_TILE        spmO, spmS, spmVall

# output
TE_MATMUL_TILE spmY, spmO, spmWo
```

---

# 13. Sync Rules

- DMA → TE/VE: 반드시 SYNC 필요  
- KV_LOAD 후 Softmax/AV: SYNC 필요  
- Accumulate MatMul tile 간: SYNC 필요  

---

# 14. Validation Rules

- DRAM 주소 일치 및 burst alignment  
- tile shape 및 dtype 일관성  
- LN, Softmax 등 reduction dim 정확성  
- sequential dependency 보존  
- KV-range validity  

---

# End of Document
