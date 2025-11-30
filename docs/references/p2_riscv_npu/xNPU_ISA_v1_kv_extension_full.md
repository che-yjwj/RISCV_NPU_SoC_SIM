
# xNPU ISA v1 — KV-Extension Included  
**Full Instruction Set Specification (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

본 문서는 xNPU ISA v1의 **풀버전 사양(Full Specification)**으로,  
기존 TE/VE/DMA 중심 명령어에 더해 **KV-cache 확장(KV Extension)**을 포함한  
현대 LLM 디코딩 워크로드 지원용 명령어 집합을 정의한다.

xNPU ISA v1은 다음과 같은 특징을 갖는다:

- Tile-centric 연산 모델  
- DRAM burst-load/store DMA 기반  
- TE(MatMul)/VE(Vector Ops)/DMA/Sync 엔진 기반  
- KV-store / KV-load 전용 ISA 제공  
- 64-bit fixed-width encoding  
- RISC-V host offload 및 descriptor 기반 스트림 제출 방식  

---

# 1. ISA Encoding Overview

## 1.1 Instruction Format (64-bit)

xNPU ISA v1 명령어는 모두 **64-bit 고정 길이**이며 다음 공통 포맷을 따른다.

```
|63        56|55     48|47     40|39     32|31                  0|
|  OPCODE    |   DST    |  SRC0   |  SRC1   |      IMMEDIATE      |
```

- `OPCODE` : 8 bits  
- `DST`    : 8 bits  
- `SRC0`   : 8 bits  
- `SRC1`   : 8 bits  
- `IMM32`  : 32 bits  

---

# 2. Instruction Categories

1. **DMA Instructions**  
2. **Tensor Engine Instructions (TE)**  
3. **Vector Engine Instructions (VE)**  
4. **KV-cache Extension Instructions**  
5. **Synchronization Instructions**  
6. **Config Instructions**

---

# 3. Opcode Table

| Category | Instruction | Opcode (Hex) |
|----------|-------------|--------------|
| DMA | DMA_LOAD_TILE | 0x01 |
| DMA | DMA_STORE_TILE | 0x02 |
| DMA | DMA_LOAD_EMBED_TILE | 0x03 |
| TE | TE_MATMUL_TILE | 0x10 |
| TE | TE_QKT_TILE | 0x11 |
| TE | TE_AV_TILE | 0x12 |
| VE | VE_GELU_TILE | 0x20 |
| VE | VE_SOFTMAX_TILE | 0x21 |
| VE | VE_RMSNORM_TILE | 0x22 |
| KV | KV_STORE_TILE | 0x30 |
| KV | KV_LOAD_TILE | 0x31 |
| SYNC | SYNC_WAIT | 0x40 |
| SYNC | SYNC_GROUP | 0x41 |
| CONFIG | CONFIG_TILE | 0x50 |
| CONFIG | CONFIG_CORE | 0x51 |

---

# 4. Detailed Instruction Specification

## 4.1 DMA Instructions

### DMA_LOAD_TILE (0x01)

**DRAM → SPM tile load**

```
DST  = spm_buffer_id
IMM32 = dram_address
```

---

### DMA_STORE_TILE (0x02)

**SPM → DRAM tile store**

```
SRC0 = spm_buffer_id
IMM32 = dram_address
```

---

### DMA_LOAD_EMBED_TILE (0x03)

Embedding vector DRAM load.

---

# 4.2 Tensor Engine Instructions (TE)

### TE_MATMUL_TILE (0x10)

```
DST = output_tile
SRC0 = A_tile
SRC1 = B_tile
```

### TE_QKT_TILE (0x11)

Q × Kᵀ tile matmul.

### TE_AV_TILE (0x12)

Attention weighted value tile matmul.

---

# 4.3 Vector Engine Instructions (VE)

### VE_GELU_TILE (0x20)
### VE_SOFTMAX_TILE (0x21)
### VE_RMSNORM_TILE (0x22)

Each applies tile-level vector transformations.

---

# 5. KV-Extension Instructions (Core Section)

## 5.1 KV_STORE_TILE (0x30)

새 Key/Value timestep을 KV-cache DRAM에 append.

**Encoding**
```
OPCODE = 0x30
DST    = head_id
SRC0   = spm_tile_index
SRC1   = 0 (K) or 1 (V)
IMM32  = dram_base_address
```

---

## 5.2 KV_LOAD_TILE (0x31)

Attention 계산을 위해 K/V range를 DRAM에서 fetch.

**Encoding**
```
OPCODE = 0x31
DST    = spm_dest_tile
SRC0   = head_id
SRC1   = 0 (K) or 1 (V)
IMM32  = kv_range_descriptor_ptr
```

### kv_range_descriptor Structure

```
struct KvRangeDesc {
    uint32_t t_start;
    uint32_t t_len;
    uint32_t d_start;
    uint32_t d_len;
}
```

---

# 6. Synchronization Instructions

### SYNC_WAIT (0x40)
Fence tile operations until completion.

### SYNC_GROUP (0x41)
Group barrier.

---

# 7. Tile Metadata Instructions

### CONFIG_TILE (0x50)

Tile metadata load into NPU tile table.

### CONFIG_CORE (0x51)

TE/VE compute kernel config.

---

# 8. Instruction Execution Semantics

## 8.1 DMA + TE Example

```
DMA_LOAD_TILE   spm0, addrA
DMA_LOAD_TILE   spm1, addrB
SYNC_WAIT
TE_MATMUL_TILE  spm2, spm0, spm1
SYNC_WAIT
DMA_STORE_TILE  spm2, addrC
```

---

## 8.2 KV Store Example

```
DMA_LOAD_TILE   spmK, addrK
KV_STORE_TILE   head0, spmK, K, kv_addr_k

DMA_LOAD_TILE   spmV, addrV
KV_STORE_TILE   head0, spmV, V, kv_addr_v
```

---

## 8.3 KV Load Example

```
KV_LOAD_TILE spm_load, head0, K, kv_range_ptr
SYNC_WAIT
```

---

# 9. Binary Encoding Details

| Bits | Field | Description |
|------|--------|-------------|
| 63:56 | OPCODE | Instruction type |
| 55:48 | DST | destination tile |
| 47:40 | SRC0 | source tile 0 |
| 39:32 | SRC1 | source tile 1 |
| 31:0 | IMM32 | address or descriptor |

---

# 10. ISA Validation Rules

- Burst alignment required for DMA & KV ops  
- KV_LOAD out-of-range is illegal  
- KV_STORE must follow per-head write pointer  
- TE/VE ops require valid SPM buffers  
- SYNC mandatory between dependent tiles  

---

# 11. Future ISA Extensions

- FlashAttention hardware kernels  
- Multi-chip KV distribution ISA  
- 96-bit long-immediate encoding  
- Specialized ISA for rotary embedding  

---

# End of Document
