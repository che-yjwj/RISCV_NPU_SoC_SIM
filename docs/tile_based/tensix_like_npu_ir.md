# Tensix-like NPU IR Specification (Draft v0.1)

## 0. Document Scope
This document defines a **Tensix-inspired NPU Intermediate Representation (IR)** intended for:
- Deterministic, cycle-based NPU simulation
- Software-driven execution control
- Tile-based LLM inference (Prefill / Decode)

This IR is **not a virtual ISA** and **not a hardware RTL contract**.
It is an *executable architectural specification* between compiler and simulator.

---

## 1. Design Philosophy

### 1.1 Core Principles
1. **Determinism First**
2. **Explicit Data Movement**
3. **Temporal Execution**
4. **Tile as the Atomic Unit**
5. **Software-Orchestrated Hardware**

### 1.2 What Is Explicitly Excluded
- Caches / coherence
- Dynamic scheduling
- Speculative execution
- Implicit parallelism

---

## 2. IR Position in the Stack

```
ONNX / PyTorch
   ↓
Graph Normalize & Fusion
   ↓
Tiling & Memory Planning
   ↓
Tensix-like NPU IR  ← (this spec)
   ↓
Descriptor / Command Queue
   ↓
Cycle-based NPU Simulator
```

---

## 3. Execution Model

### 3.1 Core Mapping
- One IR stream per NPU core
- One software thread per core
- Static scheduling only

### 3.2 Temporal Rule
At any given cycle:
- At most one **Compute** op per core
- Data Movement may overlap with Compute
- Compute–Compute overlap is forbidden

---

## 4. Memory Model

### 4.1 Memory Spaces

| Space | Scope | Latency | Notes |
|---|---|---|---|
| DRAM | Global | High | Explicit DMA only |
| SRAM | Per-core | Low | Software-managed |
| REG  | Engine-local | Minimal | Invisible to IR |

No cache abstraction exists.

### 4.2 Residency Rules
- Tiles must be explicitly resident in SRAM before compute
- Residency lifetime is compiler-controlled

---

## 5. Tile Abstraction

### 5.1 Tile Descriptor

```yaml
Tile:
  id: tile_q_17
  shape: [32, 32]
  dtype: int8
  layout: row_major
  residency: SRAM
```

### 5.2 Tile Constraints
- Fixed shape per hardware generation
- No partial tiles
- Padding handled above IR

---

## 6. Instruction Set

### 6.1 Data Movement Ops

```yaml
LOAD_TILE:
  src: DRAM
  dst: SRAM
  tile: tile_k_17
  async: true
```

```yaml
STORE_TILE:
  src: SRAM
  dst: DRAM
  tile: tile_out_17
```

### 6.2 Compute Ops (Matrix Engine)

```yaml
MATMUL_TILE:
  A: tile_q_17
  B: tile_k_17
  C: tile_attn_17
```

### 6.3 Vector Ops (Vector Engine)

```yaml
SOFTMAX_TILE:
  input: tile_attn_17
  output: tile_attn_sm_17
```

### 6.4 Synchronization

```yaml
BARRIER:
  scope: core
```

---

## 7. Execution Timeline Example

```
Cycle →
LOAD(tile_k) ─────┐
                   ├─ overlap
        MATMUL     ┘
        SOFTMAX
```

---

## 8. Simulator Requirements
- Global cycle counter
- Explicit SRAM occupancy tracking
- Tile lifetime visualization
- Deterministic replay

---

## 9. Future Extensions
- KV-cache residency hints
- NoC multicast primitives
- Power / energy annotations

---
End of Specification
