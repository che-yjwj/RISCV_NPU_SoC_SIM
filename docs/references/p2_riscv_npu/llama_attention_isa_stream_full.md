
# LLaMA Attention ISA Stream — IA_RISC_V_NPU_Simulator v2  
**Full Technical Example (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team

---

# 0. Purpose

본 문서는 **LLaMA Self-Attention** 연산을  
**tile decomposition → lowering → full xNPU ISA stream**  
순서로 완전한 end‑to‑end 예시로 정리한다.

이 문서는 다음 내용을 포함한다:

- Q, K, V projection에 대한 tile-level ISA  
- KV-store(K_t, V_t append) ISA  
- KV-load(all previous K/V range) ISA  
- QKᵀ → Softmax → Attn·V tile ISA  
- Output projection tile ISA  
- 전체 ISA stream을 timestep t 기준으로 하나의 연속된 명령 시퀀스 형태로 제공  
- DRAM 주소/타일 ID/헤드 인덱스/head-offset을 모두 포함  

LLM 디코딩 과정에서 실제 NPU가 실행하는 ISA 패턴을 재현한다.

---

# 1. Tile Metadata Used in This Example

예시를 위해 아래와 같은 가상의 타일/주소 메타데이터를 가정한다.

```
SPM tile buffers:
  spmX    = 0x01
  spmQ    = 0x02
  spmK    = 0x03
  spmV    = 0x04
  spmKall = 0x05
  spmVall = 0x06
  spmScore= 0x07
  spmO    = 0x08
  spmY    = 0x09

Wq_addr   = 0x1000_0000
Wk_addr   = 0x1001_0000
Wv_addr   = 0x1002_0000
Wout_addr = 0x1003_0000

X_addr    = 0x2000_0000
Y_addr    = 0x2001_0000

KV cache layout (per head):
  base_k = 0x3000_0000
  base_v = 0x3100_0000

timestep t = 5 (append at index 5)
kv_addr_k_t = base_k + 5 * TILE_BYTES
kv_addr_v_t = base_v + 5 * TILE_BYTES

kv_range_desc_ptr = 0x4000_1000   # describes [0..5]
head_id = 3
```

---

# 2. QKV Projection — ISA Stream

Q = X·Wq  
K = X·Wk  
V = X·Wv

```
# Load input tile X
DMA_LOAD_TILE     DST=spmX     IMM=X_addr

# Q projection
DMA_LOAD_TILE     DST=spmWq    IMM=Wq_addr
SYNC_WAIT
TE_MATMUL_TILE    DST=spmQ     SRC0=spmX   SRC1=spmWq

# K projection
DMA_LOAD_TILE     DST=spmWk    IMM=Wk_addr
SYNC_WAIT
TE_MATMUL_TILE    DST=spmK     SRC0=spmX   SRC1=spmWk

# V projection
DMA_LOAD_TILE     DST=spmWv    IMM=Wv_addr
SYNC_WAIT
TE_MATMUL_TILE    DST=spmV     SRC0=spmX   SRC1=spmWv
```

---

# 3. KV Cache Store — ISA Stream

KV-store는 K_t, V_t를 KV-cache DRAM에 append한다.

```
# Store current timestep K_t, V_t
KV_STORE_TILE     DST=head_id=3  SRC0=spmK  SRC1=K  IMM=kv_addr_k_t
KV_STORE_TILE     DST=head_id=3  SRC0=spmV  SRC1=V  IMM=kv_addr_v_t
SYNC_GROUP
```

---

# 4. KV Load (Range Fetch) — ISA Stream  
KV-load는 `[0..t]` 범위 전체를 fetch한다.

```
KV_LOAD_TILE      DST=spmKall   SRC0=head_id=3  SRC1=K  IMM=kv_range_desc_ptr
KV_LOAD_TILE      DST=spmVall   SRC0=head_id=3  SRC1=V  IMM=kv_range_desc_ptr
SYNC_WAIT
```

---

# 5. Attention Score (QKᵀ) — ISA Stream

```
TE_QKT_TILE       DST=spmScore  SRC0=spmQ   SRC1=spmKall
SYNC_WAIT
```

---

# 6. Softmax — ISA Stream

```
VE_SOFTMAX_TILE   DST=spmScore  SRC0=spmScore
SYNC_WAIT
```

---

# 7. Attention Aggregation (Attn·V) — ISA Stream

```
TE_AV_TILE        DST=spmO      SRC0=spmScore   SRC1=spmVall
SYNC_WAIT
```

---

# 8. Output Projection — ISA Stream

```
DMA_LOAD_TILE     DST=spmWout   IMM=Wout_addr
SYNC_WAIT
TE_MATMUL_TILE    DST=spmY      SRC0=spmO   SRC1=spmWout
DMA_STORE_TILE    SRC0=spmY     IMM=Y_addr
```

---

# 9. Full LLaMA Attention ISA Stream (Concatenated)

아래는 위 모든 단계를 하나의 연속된 ISA 시퀀스로 나열한 결과이다.

```
# ---------------------
# 1. Load X
DMA_LOAD_TILE      spmX, X_addr

# ---------------------
# 2. QKV projection
DMA_LOAD_TILE      spmWq, Wq_addr
SYNC_WAIT
TE_MATMUL_TILE     spmQ, spmX, spmWq

DMA_LOAD_TILE      spmWk, Wk_addr
SYNC_WAIT
TE_MATMUL_TILE     spmK, spmX, spmWk

DMA_LOAD_TILE      spmWv, Wv_addr
SYNC_WAIT
TE_MATMUL_TILE     spmV, spmX, spmWv

# ---------------------
# 3. KV-store
KV_STORE_TILE      head=3, spmK, K, kv_addr_k_t
KV_STORE_TILE      head=3, spmV, V, kv_addr_v_t
SYNC_GROUP

# ---------------------
# 4. KV-load
KV_LOAD_TILE       spmKall, head=3, K, kv_range_desc_ptr
KV_LOAD_TILE       spmVall, head=3, V, kv_range_desc_ptr
SYNC_WAIT

# ---------------------
# 5. QKᵀ attention score
TE_QKT_TILE        spmScore, spmQ, spmKall
SYNC_WAIT

# ---------------------
# 6. Softmax
VE_SOFTMAX_TILE    spmScore, spmScore
SYNC_WAIT

# ---------------------
# 7. Attn·V
TE_AV_TILE         spmO, spmScore, spmVall
SYNC_WAIT

# ---------------------
# 8. Output projection
DMA_LOAD_TILE      spmWout, Wout_addr
SYNC_WAIT
TE_MATMUL_TILE     spmY, spmO, spmWout
DMA_STORE_TILE     spmY, Y_addr
```

---

# 10. ISA Count Summary

| Stage | # ISA |
|--------|--------|
| QKV projection | 9 |
| KV-store | 3 |
| KV-load | 3 |
| QKᵀ | 2 |
| Softmax | 2 |
| Attn·V | 2 |
| Output projection | 4 |
| **Total** | **25 instructions** |

---

# End of Document
