# LLaMA Attention in Tensix-like NPU IR

## 0. Purpose
This document provides a **fully explicit, tile-level Tensix-style IR example**
for a single LLaMA attention block.
It is intended as a **ground-truth executable example** for NPU simulators.

---

## 1. Target Model Scope

- Model: LLaMA-style Transformer
- Focus: Single Attention Block
- Phase Coverage:
  - Prefill (full sequence)
  - Decode (single token)

---

## 2. Tensor Decomposition

| Tensor | Shape (logical) | Tile Shape |
|------|---------------|-----------|
| Q | [T, H, D] | 32x32 |
| K | [T, H, D] | 32x32 |
| V | [T, H, D] | 32x32 |

All tensors are decomposed into **fixed 32x32 tiles**.

---

## 3. Prefill Phase IR (Per Core)

### 3.1 Load Q/K Tiles

```yaml
LOAD_TILE:
  src: DRAM
  dst: SRAM
  tile: Q[t,h]

LOAD_TILE:
  src: DRAM
  dst: SRAM
  tile: K[t',h]
```

---

### 3.2 Attention Score (Q × Kᵀ)

```yaml
MATMUL_TILE:
  A: Q[t,h]
  B: K[t',h]
  C: ATT[t,t',h]
```

---

### 3.3 Softmax (Vector Engine)

```yaml
SOFTMAX_TILE:
  input: ATT[t,t',h]
  output: ATT_SM[t,t',h]
```

---

### 3.4 Weighted Sum (Attention × V)

```yaml
LOAD_TILE:
  src: DRAM
  dst: SRAM
  tile: V[t',h]

MATMUL_TILE:
  A: ATT_SM[t,t',h]
  B: V[t',h]
  C: OUT[t,h]
```

---

## 4. Prefill Memory Residency

- Q/K/V streamed from DRAM
- ATT and ATT_SM transient in SRAM
- OUT optionally written back to DRAM

---

## 5. Decode Phase IR (Single Token)

### 5.1 Assumptions
- K/V tiles are **pinned in SRAM**
- Only Q is streamed per token

---

### 5.2 Decode Attention IR

```yaml
LOAD_TILE:
  src: DRAM
  dst: SRAM
  tile: Q[t_new,h]

MATMUL_TILE:
  A: Q[t_new,h]
  B: K_cached[h]
  C: ATT[h]

SOFTMAX_TILE:
  input: ATT[h]
  output: ATT_SM[h]

MATMUL_TILE:
  A: ATT_SM[h]
  B: V_cached[h]
  C: OUT[t_new,h]
```

---

## 6. Temporal Execution Timeline

```
Cycle →
LOAD(Q) ─────┐
              ├─ overlap
        MATMUL(QK)
        SOFTMAX
        MATMUL(AV)
```

Compute ops are serialized; DMA overlaps where possible.

---

## 7. Determinism Guarantees

- Fixed tile order
- Fixed core assignment
- Fixed memory residency
- Replayable cycle trace

---

## 8. Simulator Validation Checklist

- Tile lifetime correctness
- SRAM capacity enforcement
- Prefill → Decode phase switch
- Decode latency upper bound

---

End of Example
