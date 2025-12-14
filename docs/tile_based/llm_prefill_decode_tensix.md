# LLM Prefill / Decode Scheduling (Tensix Style)

## 0. Purpose
This document defines a **Tensix-style scheduling model** for LLM inference,
explicitly separating **Prefill** and **Decode** execution phases.

---

## 1. Phase Overview

| Phase | Objective | Dominant Cost |
|---|---|---|
| Prefill | Throughput | DRAM BW + GEMM |
| Decode | Latency | Control + SRAM reuse |

---

## 2. Prefill Scheduling Model

### 2.1 Execution Strategy
- Sequence × Head × Tile decomposition
- High tile concurrency across cores
- KV cache streamed from DRAM

### 2.2 Prefill IR Pattern

```yaml
LOAD_TILE   Q[t,h]
LOAD_TILE   K[t,h]
MATMUL_TILE Q K -> A
SOFTMAX_TILE A -> A'
STORE_TILE  A'
```

### 2.3 Characteristics
- Aggressive DMA
- NoC multicast opportunities
- Compute-bound when tiled correctly

---

## 3. Decode Scheduling Model

### 3.1 Key Insight
**KV cache is state, not data**.

### 3.2 Execution Strategy
- KV tiles pinned in SRAM
- Only Q tiles loaded per token
- Minimal DMA traffic

### 3.3 Decode IR Pattern

```yaml
LOAD_TILE   Q[t]
MATMUL_TILE Q K_cached -> A
SOFTMAX_TILE A -> A'
MATMUL_TILE A' V_cached -> O
```

---

## 4. Prefill → Decode Transition

### 4.1 State Change
- KV residency switches from DRAM-managed to SRAM-pinned
- Tile eviction forbidden during Decode

### 4.2 Scheduler Implications
- Core assignment becomes stable
- DMA engine mostly idle

---

## 5. Determinism Guarantees
- Fixed instruction order
- Fixed memory access pattern
- Cycle-level replayable behavior

---

## 6. Simulator Implementation Checklist
- Phase-aware execution mode
- SRAM pin/unpin support
- Decode latency upper-bound reporting
- Gantt-style timeline visualization

---

## 7. Architectural Implications
- Mobile NPUs benefit more than server GPUs
- Power predictability improves
- Worst-case latency is analyzable

---
End of Document
