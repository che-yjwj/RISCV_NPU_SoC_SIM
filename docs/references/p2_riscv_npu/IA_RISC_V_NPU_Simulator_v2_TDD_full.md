
# TDD: IA_RISC_V_NPU_Simulator v2  
Technical Design Document (Full Version, Ultra‑Long)

Version: 1.0  
Status: Complete Draft  
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Overview

This Technical Design Document (TDD) defines the **full engineering design** for the  
**IA_RISC_V_NPU_Simulator v2**, which models:

- PyTorch/ONNX/DSL frontend  
- IR graph normalization & shape inference  
- Tiling engine  
- TileOpGraph construction  
- Static + Dynamic schedulers  
- xNPU ISA generation  
- Py‑V RISC‑V host interaction  
- NPU multi-core execution (TE/VE/DMA/SPM)  
- DRAM/NoC cycle-level modeling  
- KV-cache engine (append & range-load)  
- Full timeline & profiling pipeline  

This document describes **modules, data structures, algorithms, interfaces, and invariants**  
needed for full implementation.

---

# 1. System Architecture

## 1.1 High-Level Flow

```
PyTorch / ONNX / DSL
        ↓
Frontend Normalization
        ↓
IR Graph
        ↓
Tiling Engine
        ↓
TileOpGraph (tile-level DAG)
        ↓
Scheduler (static → dynamic)
        ↓
xNPU ISA Streams
        ↓
Py-V Host CPU
        ↓
NPU Runtime (TE/VE/DMA/SPM)
        ↓
DRAM / NoC Model
        ↓
Profiler (Timeline, BW, Utilization)
```

---

# 2. Frontend Design

## 2.1 PyTorch FX Frontend

### Components
- `fx_tracer.py`: Extracts FX graph  
- `fx_normalizer.py`:  
  - Remove extraneous ops  
  - Normalize linear/bmm/permute  
- `fx_to_ir.py`: Convert FX nodes → IRNode structures

### Key Responsibilities
- Map operations to canonical IR ops  
- Extract tensor shapes  
- Detect structured patterns (QKV projection, GLU, FFN)

---

## 2.2 ONNX Frontend

### Components
- `onnx_loader.py`
- `onnx_normalizer.py`
- `onnx_to_ir.py`

### Responsibilities
- Handle opset differences  
- Fuse operator subgraphs  
- Convert to IRGraph with uniform semantics

---

## 2.3 DSL Frontend

### Goal  
Custom minimal DSL to quickly describe compute graphs.

### Process  
DSL → parse tree → IRGraph

---

# 3. IR System

## 3.1 IRGraph Structure

```
class IRGraph:
    nodes: List[IRNode]
    edges: Dict[node_id, List[node_id]]
```

## 3.2 IRNode

```
class IRNode:
    id
    op_type              # MatMul, Conv2D, Softmax, KVStore, KVLoad…
    inputs               # source IRNode IDs
    outputs              # output tensor IDs
    attrs                # kernel, stride, head count, axis…
    shape                # inferred tensor shape
    dtype
```

---

## 3.3 Passes

### 3.3.1 Canonicalization
- Reshape/transpose folding  
- Linear → MatMul + Bias  
- QKV pattern extraction

### 3.3.2 Fusion
- MatMul + Add + GELU → FusedFFN  
- Q/K/V linear → AttentionQKV

### 3.3.3 Shape Inference
Static evaluator that propagates tensor shapes.

### 3.3.4 Dead Code Elimination
Prune unreachable IR nodes.

---

# 4. Tiling Engine

## 4.1 TileDesc

```
class TileDesc:
    tensor_id
    shape
    offset
    dram_base
    dram_size
    spm_size
    dtype_bytes
```

---

## 4.2 MatMul Tiling Algorithm

Given `[M,K] x [K,N]`:

1. Select M_tile, N_tile, K_tile based on:
   - SPM size  
   - DRAM burst size  
   - TE array shape  
2. Generate tiles:
   - `(m_idx, n_idx, k_idx)` loops  
3. Compute DRAM ranges:
   - `A[m_offset : m_offset+M_tile, k_offset:...]`
   - `B[...]`
   - `C partial`

---

## 4.3 Conv2D Tiling

Block over:
- Cout  
- Hin / Win  
- Cin  

Include stride/padding/dilation in slicing.

---

## 4.4 Attention Tiling

### Q/K/V
Tile over:  
- batch  
- head  
- sequence length T  
- head dimension D_head  

### KV-cache tiles
Represent time segments `[t0 … t1]` and sub-dimension slices.

---

## 4.5 TileOpNodes

```
class TileOpNode:
    id
    op_type          # MATMUL, CONV2D, KV_STORE_TILE, KV_LOAD_TILE …
    input_tiles      # TileDesc[]
    output_tiles     # TileDesc[]
    deps             # predecessor TileOpNodes
    cost_estimate
```

---

# 5. TileOpGraph Construction

## 5.1 Dependency Rules

- MatMul:  
  K-split tiles → partial sums  
  N/M tiles → independent  
- Attention:  
  KV store → KV load → Score → Softmax → Attn·V  
- Conv:  
  Sliding window dependencies  

---

## 5.2 Graph Build Algorithm

```
for ir_node in topo_sorted_IR:
    tiles = tiler.tile(ir_node)
    for tile in tiles:
        create TileOpNode
        connect dependencies:
            - based on IR dataflow
            - tile-local dependencies
```

---

# 6. Scheduler Design

## 6.1 Static Scheduler

### Goal  
Generate initial core assignment & tile order.

### Algorithm  

1. Compute critical path length for each TileOpNode.  
2. Sort by decreasing priority.  
3. Assign tiles to cores in round-robin or cost-aware manner.

---

## 6.2 Dynamic Scheduler

### Purpose  
Resolve resource contention at runtime:

- Core busy/idle  
- DRAM/NoC availability  
- SPM buffer state  

### Main Loop

```
while not done:
    update all cores
    update dram/noc
    push completed successors to ready queue
    assign ready tiles to idle cores
```

---

# 7. ISA Generator

## 7.1 ISA Format

64-bit instruction:

```
[ opcode | dst | src0 | src1 | src2 | imm16 ]
```

Full opcode list is defined in xNPU_ISA_v1_kv_extension.md.

---

## 7.2 Lowering Pipeline

For each TileOpNode:

- MatMul  
  1. DMA load A/B/C  
  2. TE_MATMUL_TILE  
  3. DMA store result  

- Softmax  
  1. DMA load tile  
  2. VE_SOFTMAX_TILE  
  3. DMA store tile  

- KV-store  
  - KV_STORE_TILE  
- KV-load  
  - KV_LOAD_TILE

---

## 7.3 Per-Core Stream Builder

```
core_streams[core_id].append(instruction)
```

Ensures ordering constraints preserved.

---

# 8. Py‑V Host CPU Integration

## 8.1 RISC-V Extensions

Pseudo instructions:

- `XNPU_SUBMIT stream_ptr`
- `XNPU_WAIT completion_ptr`

## 8.2 Host Responsibilities

- Build command descriptor  
- Write descriptor to MMIO  
- Ring doorbell  
- Poll completion queue  

---

# 9. NPU Runtime

## 9.1 Core Structure

Each NPU core contains:

- Cmd Fetch/Decode  
- TE (Tensor Engine)  
- VE (Vector Engine)  
- DMA Engine  
- SPM (Scratchpad)  

---

## 9.2 TE Engine Model

Analytic latency:

```
cycles = pipeline_depth + (MACs / (array_m * array_n))
```

Support:
- MatMul tiles  
- Attn·V tiles  
- QKᵀ tiles  

---

## 9.3 VE Engine Model

Handles:
- Softmax  
- LayerNorm  
- GELU  
- RMSNorm  

Latency = analytic function of vector width and tile size.

---

## 9.4 DMA Engine Model

- Queue of DMA requests  
- Issue DRAM burst commands  
- Interact with NoC for routing  
- Maintains SPM read/write buffers

---

# 10. DRAM / NoC Model

## 10.1 DRAM

- Channels  
- Banks  
- Row buffers  
- Queues  

### Timing  

Simplified timing:
- tRCD, tCL, tRP aggregated  
- Modeled via burst + bank/row latency  

---

## 10.2 NoC

- Mesh or ring  
- Link-level bandwidth  
- Arbitration policies  

Every DMA request becomes:
- Packets → routed → DRAM controller → return packets

---

# 11. KV-Cache Engine

## 11.1 KvDescTable

```
struct KvDesc {
    head_id
    time_start
    time_len
    d_start
    d_len
    base_addr
    dtype_bytes
}
```

---

## 11.2 KV-Store

- Write newly computed (K_t, V_t)  
- DRAM aligned writes  
- Update KvDescTable

---

## 11.3 KV-Load

- Compute range `[t0 … t1]`  
- Split into tiles  
- Burst-align DRAM loads  
- Issue KV_LOAD_TILE instructions

---

# 12. Timeline & Profiler

## 12.1 Events Logged

- TE start / end  
- VE start / end  
- DMA issue / finish  
- DRAM queueing / service  
- NoC routing  
- Tile completion  

---

## 12.2 Output

- JSON timeline  
- CSV per-engine utilization  
- Gantt chart visualization  
- DRAM bandwidth chart  
- Tile latency breakdown

---

# 13. Module Interfaces (API)

## 13.1 Tiler API

```
tiles = tiler.tile(ir_node)
```

## 13.2 Scheduler API

```
schedule = scheduler.run(tile_graph)
```

## 13.3 ISA Generation

```
isa_streams = isa_gen.lower(schedule)
```

## 13.4 NPU Tick Loop

```
while not done:
    npu.tick()
    dram.tick()
    noc.tick()
    profiler.tick()
```

---

# 14. Invariants

1. **Tile Coverage 100%**  
   Every IR op must be mapped to tiles.

2. **ISA Consistency**  
   Tiles must produce valid ISA.

3. **SPM Safety**  
   No tile may exceed SPM.

4. **Dependency Safety**  
   Scheduler cannot violate DAG ordering.

5. **Memory Safety**  
   All DRAM addresses must match TileDesc metadata.

---

# 15. Testing Plan

## 15.1 Unit Tests
- IR passes  
- Tiler correctness  
- TileOpGraph dependencies  
- ISA lowering correctness  

## 15.2 Integration Tests
- LLaMA block  
- KV-store/load correctness  
- DRAM burst alignment tests  

## 15.3 Performance Tests
- Timeline correctness  
- DRAM/NoC bandwidth  
- Multi-core scaling  

---

# 16. Future Extensions

- FlashAttention tiler  
- GQA support  
- Multi-chip NoC  
- RL-based scheduler  
- Automatic tiling search  

---

# End of Document
