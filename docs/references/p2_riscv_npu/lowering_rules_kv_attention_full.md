
# Lowering Rules for KV-Attention — IA_RISC_V_NPU_Simulator v2  
**Full Technical Design Document (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team

---

# 0. Purpose

본 문서는 **KV-Cache 기반 Attention 연산(Q, K, V projection → KV store → KV load → QKᵀ → Softmax → Attn·V → Output projection)**을  
타일 기반 **xNPU ISA 스트림**으로 변환하는 정식 **Lowering Rule (타일→ISA 변환 규칙)**을 상세하게 규정한다.

KV-cache는 디코딩 단계에서 핵심 병목이므로, lowering은 다음 특성을 만족해야 한다:

- 시간축 KV 누적에 대한 정확한 DRAM 레이아웃 유지  
- per-head KV-store 동기화  
- KV-load 범위(descriptor) 기반 DMA 스트림 생성  
- TE/VE tile scheduling 고려  
- FlashAttention-like 최적화를 위한 확장성  
- QKV Projection → Attention → Output 전체 파이프라인을 타일 수준으로 완전하게 기술  

---

# 1. High-Level KV-Attention Flow

LLM 디코딩 1 step에 대해 lowering은 다음 순서를 따른다.

```
1. Q, K, V 생성 (MatMul)
2. 새 K_t, V_t를 KV-cache에 append (KV_STORE_TILE)
3. 전체 past K, V 범위를 DRAM에서 fetch (KV_LOAD_TILE)
4. Attention score(QKᵀ) 계산 (TE_QKT_TILE)
5. Softmax (VE_SOFTMAX_TILE)
6. Aggregation(Attn·V) (TE_AV_TILE)
7. Output projection (MatMul)
8. output tile store
```

---

# 2. Tile Metadata Requirements

KV-attention lowering에는 다음 메타데이터가 필요하다:

### Required fields

| Field | Description |
|-------|-------------|
| head_id | KV-cache head index |
| t_new | 현재 timestep index |
| tile_shape(K/V) | (tile_seq, tile_dim) |
| kv_cache_base | DRAM base for KV-cache |
| kv_range_desc_ptr | KV_LOAD_TILE descriptor address |
| q_tile_id / k_tile_id / v_tile_id | SPM buffer index |

모든 lowering 규칙은 이 메타데이터 구조를 참조한다.

---

# 3. Lowering Step 1 — QKV Projection

입력 X에 대해:

```
Q = X * Wq
K = X * Wk
V = X * Wv
```

### Lowering Sequence

```
DMA_LOAD_TILE spmX, X_addr

DMA_LOAD_TILE spmWq, Wq_addr
SYNC_WAIT
TE_MATMUL_TILE spmQ, spmX, spmWq

DMA_LOAD_TILE spmWk, Wk_addr
SYNC_WAIT
TE_MATMUL_TILE spmK, spmX, spmWk

DMA_LOAD_TILE spmWv, Wv_addr
SYNC_WAIT
TE_MATMUL_TILE spmV, spmX, spmWv
```

Bias/GELU는 projection 단계에는 포함되지 않음.

---

# 4. Lowering Step 2 — KV-Store (Append)

새 timestep에 대한 Key_t, Value_t를 KV-cache에 저장한다.  

### xNPU ISA
```
KV_STORE_TILE (opcode 0x30)
```

### Lowering Rule

```
KV_STORE_TILE head_id, spmK, K, kv_addr_k_t
KV_STORE_TILE head_id, spmV, V, kv_addr_v_t
```

여기서 kv_addr_k_t는 다음을 반영해 계산한다:

```
kv_addr_base + head_id * HEAD_STRIDE + t_new * TILE_BYTES(K)
```

KV-store는 반드시 `SYNC_WAIT` 없이도 순차적 append지만, 다음 조건에서는 fence 필요:

- 같은 head에 대해 K→V 순서를 보장해야 할 때  
- 다음 timestep과 interleave 방지  

따라서 lowering은 자동으로 삽입:

```
SYNC_GROUP    # ensure K_t and V_t committed
```

---

# 5. Lowering Step 3 — KV-Load (Range Fetch)

이전 timesteps `[0..t_new]` 에 대한 K/V 전체 범위를 load.

### xNPU ISA
```
KV_LOAD_TILE (opcode 0x31)
```

### KV Range Descriptor

```
struct KvRangeDesc {
    uint32_t t_start;
    uint32_t t_len;
    uint32_t d_start;
    uint32_t d_len;
}
```

### Lowering Rule

```
KV_LOAD_TILE spmK_all, head_id, K, kv_range_desc_ptr
KV_LOAD_TILE spmV_all, head_id, V, kv_range_desc_ptr
SYNC_WAIT
```

주의: load range는 tile 단위이므로, scheduler는 KV tiling layout을 이미 생성해 둔다.

---

# 6. Lowering Step 4 — QKᵀ (Attention Scores)

타일 단위 TE 연산:

```
TE_QKT_TILE(spmScore, spmQ, spmK_all)
```

Lowering:

```
TE_QKT_TILE spmScore, spmQ, spmK_all
SYNC_WAIT
```

출력 tile spmScore는 softmax dimension에 맞게 shape을 갖는다.

---

# 7. Lowering Step 5 — Softmax

Sequence-axis softmax:

```
VE_SOFTMAX_TILE spmScore, spmScore
SYNC_WAIT
```

---

# 8. Lowering Step 6 — Attention Aggregation (Attn·V)

```
O = Softmax(QKᵀ) · V
```

Lowering:

```
TE_AV_TILE spmO, spmScore, spmV_all
SYNC_WAIT
```

---

# 9. Lowering Step 7 — Output Projection

```
Y = O * Wout
```

Lowering:

```
DMA_LOAD_TILE spmWout, Wout_addr
SYNC_WAIT
TE_MATMUL_TILE spmY, spmO, spmWout
DMA_STORE_TILE spmY, Y_out_addr
```

---

# 10. Combined KV-Attention Lowering (Full Sequence)

아래는 하나의 timestep에 대해 생성되는 **최종 ISA 스트림** 순서이다.

```
# 1: QKV projection
DMA_LOAD_TILE spmX, X_addr
DMA_LOAD_TILE spmWq, Wq_addr
SYNC_WAIT
TE_MATMUL_TILE spmQ, spmX, spmWq

DMA_LOAD_TILE spmWk, Wk_addr
SYNC_WAIT
TE_MATMUL_TILE spmK, spmX, spmWk

DMA_LOAD_TILE spmWv, Wv_addr
SYNC_WAIT
TE_MATMUL_TILE spmV, spmX, spmWv

# 2: KV store
KV_STORE_TILE head, spmK, K, kv_addr_k_t
KV_STORE_TILE head, spmV, V, kv_addr_v_t
SYNC_GROUP

# 3: KV load (range)
KV_LOAD_TILE spmKall, head, K, kv_range_desc
KV_LOAD_TILE spmVall, head, V, kv_range_desc
SYNC_WAIT

# 4: QKᵀ
TE_QKT_TILE spmScore, spmQ, spmKall
SYNC_WAIT

# 5: softmax
VE_SOFTMAX_TILE spmScore, spmScore
SYNC_WAIT

# 6: Attn·V
TE_AV_TILE spmO, spmScore, spmVall
SYNC_WAIT

# 7: output projection
DMA_LOAD_TILE spmWout, Wout_addr
SYNC_WAIT
TE_MATMUL_TILE spmY, spmO, spmWout
DMA_STORE_TILE spmY, Y_addr
```

---

# 11. Core Sync Rules for KV-Attention

### 11.1 Must-sync rules

| Location | Reason |
|----------|--------|
| DMA_LOAD → TE | compute correctness |
| KV_STORE → KV_LOAD | DRAM commit order |
| QKᵀ → Softmax | softmax correctness |
| Softmax → AV | weight correctness |
| AV → OutputMatMul | output projection correctness |
| Final → DMA_STORE | write-back ordering |

---

# 12. Scheduler Constraints

Scheduler는 다음 제약을 적용해야 한다:

- KV_LOAD_TILE은 반드시 KV_STORE_TILE 이후  
- head별 KV-append offset 계산 필요  
- t_new 증가에 따라 kv_range_desc 업데이트  
- SPM buffer lifetime 관리  
- compute/DRAM interleave 최소화  

---

# 13. Validation Rules

- kv_range_desc 범위는 `[0..t_new]` 내에 있어야 함  
- SPM tile shape(Q,K_all,V_all)은 TE/VE HW spec과 일치해야 함  
- KV_STORE_TILE의 addr는 head별 non-overlapping  
- sequence dimension 증가(timestep 증가)에 따라 DRAM 공간 오염 없음  
- QKᵀ과 AV에서 tile dim이 매칭해야 함  

---

# 14. Future Extensions

- FlashAttention lowering rule  
- Head-split compute parallelism  
- Streaming KV-load (no full KV load)  
- Rotary embedding fused lowering  
- Multi-chip KV-cache Sharding  

---

# End of Document
