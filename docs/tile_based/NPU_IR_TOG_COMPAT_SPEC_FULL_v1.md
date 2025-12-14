# NPU-IR TOG Compatibility Specification (FULL v1.0)

Author: ChatGPT (for 창훈)
Reference: PyTorchSim TOG (PSAL-POSTECH)
Target: Static-scheduled Mobile / Edge NPU Simulator & Compiler

---

## 0. Executive Summary

This document defines a **full, executable-grade NPU-IR specification** that is **semantically compatible with PyTorchSim’s TOG (Tile Operation Graph)**, while being explicitly designed for:

- Static scheduling (mobile-class NPU)
- CMDQ / MMIO / Descriptor-based backends
- Tile-Level Simulation (TLS)
- Optional Global Cycle simulation

The IR is intended to be the **single source of truth** between compiler, simulator, and backend.

---

## 1. Background and Motivation

PyTorchSim showed that instruction-level simulation is unnecessary when compute latency is deterministic per tile and memory contention dominates.

---

## 2. Design Philosophy

1. Tile as atomic execution unit  
2. Explicit memory movement  
3. Explicit synchronization  
4. Structural loops  
5. Backend-agnostic  

---

## 3. IR Structure

```yaml
NpuProgram:
  graphs: list[NpuGraph]
```

```yaml
NpuGraph:
  nodes: map[NodeId, NpuNode]
  edges: list[Edge]
```

---

## 4. Node Types

### LoopBegin / LoopEnd

```yaml
type: LoopBegin
loop_type: PARALLEL | ACCUMULATION | INNER
```

### DMA

```yaml
type: DmaLoad | DmaStore | DmaWait
```

### ComputeTile

```yaml
type: ComputeTile
engine: TE | VE
cycles: int
```

---

## 5. Examples

### GEMM Tile

```text
DMA Load A/B → Wait → TE Compute → Store
```

### LLaMA Decode

```text
Loop(KV) → Load → Dot → Reduce
```

---

## 6. Execution Models

- TLS
- Global Cycle

---

## 7. Summary

TOG-compatible NPU-IR for static scheduling and simulation.
