
# PRD: KV-Attention Extension for IA_RISC_V_NPU_Simulator v2

Version: 1.0 Full  
Status: Complete Specification  
<!-- status: complete -->
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

This document defines the **Product Requirements** for the **KV-Attention Extension** of  
**IA_RISC_V_NPU_Simulator v2**, enabling accurate modeling of:

- KV-cache append-store operations  
- KV-range load operations  
- Decoder-step attention latency  
- Multi-head KV-layout and DRAM locality  
- Cross-step dependency, burst alignment, and NoC contention  
- Tile-level KV-store and load semantics  
- xNPU ISA KV extensions (KV_STORE_TILE, KV_LOAD_TILE)

This PRD ensures the simulator supports **LLaMA-style attention**, **multistep decoding**,  
and **high-bandwidth KV-cache workloads** as first-class citizens.

---

# 1. Problem Statement

Large Language Models rely on caching previously computed key/value vectors:

- Stored once during decode step *t*
- Loaded every future step *t+1, t+2, …*

Existing simulators poorly support:

- Multi-range KV loads  
- Per-head DRAM scatter/gather  
- Burst misalignment and DRAM bank conflicts  
- Tile-level KV behaviors  
- ISA-level KV instructions  
- KV-store latency & KV-load latency attribution  

As a result, decoder-step latency cannot be accurately predicted.

This extension addresses these issues.

---

# 2. Goals

## 2.1 Functional Goals

**FG-01. Support KV-store Append**  
- During decode, new (K_t, V_t) must be stored in DRAM with correct memory layout.

**FG-02. Support KV-load Range Access**  
- Decoder step t must load `[0 … t]` or `[t-W … t]` (sliding window).  
- Range may be discontinuous (index-trace).

**FG-03. Tile-Level KV Operations**  
- KV-store and KV-load must be expressed as tile ops.

**FG-04. Multi-Head Support**  
- Per-head DRAM placement  
- Per-head KV-store/load  
- Head-major / time-major layout selection

**FG-05. ISA-Level KV Instructions**  
- xNPU ISA must support KV_STORE_TILE, KV_LOAD_TILE.

**FG-06. DRAM/NoC Contention Modeling**  
- KV loads typically dominate memory traffic. Model fully.

**FG-07. Correct Latency Attribution**  
- Partition latency into:
  - KV-store
  - KV-load
  - Compute
  - Softmax
  - Attn·V
  - NoC / DRAM stall

---

## 2.2 Non-Functional Goals

**NFG-01. Accuracy**  
- KV-load bandwidth accuracy < ±20%  
- End-to-end decoder validation error < 10%

**NFG-02. Extensibility**  
- Support for:
  - FlashAttention KV tiling  
  - Sliding window attention  
  - Grouped-Query Attention (GQA)  
  - Sparse-KV attention  

**NFG-03. Consistency**  
- KV-store → KV-load → Timeline must be completely consistent.

---

# 3. Non-Goals

- No RTL-level precision  
- No hardware cache coherency modeling  
- No speculative KV prefetching models (future work)

---

# 4. Use Cases

## UC-1. LLaMA Decoder Step  
Simulate a full attention decode step including:  
- K_t, V_t store  
- K_{0..t}, V_{0..t} load  
- Score calculation  
- Softmax  
- Attn·V  
- Output projection  
- DRAM stall and NoC arbitration effects  

## UC-2. Sliding Window KV  
Evaluate latency when only recent W tokens are loaded.

## UC-3. Per-Head Locality Study  
Evaluate DRAM placement strategy effect on:  
- bank conflicts  
- read latency  
- row-buffer hit ratio

## UC-4. Prefill vs Decode Comparison  
Prefill: store-only  
Decode: store + major load traffic  
Compare their performance.

---

# 5. Requirements

## 5.1 Functional Requirements

### **FR-100: KV Store Semantics**
1. Store K_t and V_t tile into DRAM with correct alignment.  
2. Maintain KvDescTable with entries:
   - base address  
   - per-head offset  
   - time index  
   - dtype, bytes  
3. Update logical KV length (`t += 1`) correctly.

---

### **FR-110: KV Load Semantics**
1. Load `[t0 … t1]` range by generating tile load ops.  
2. Handle head-major or time-major DRAM allocation.  
3. Models partial-tile loading for misaligned segments.  
4. Handle multi-head KV loads in parallel or sequential state.

---

### **FR-120: KV Tiler**
KV tiler must:
- Compute tile shapes `(T_tile, D_tile)`  
- Compute DRAM ranges for each tile  
- Split long ranges into burst-aligned tiles  
- Generate TileOpNodes:
  - KV_STORE_TILE_NODE  
  - KV_LOAD_TILE_NODE  

---

### **FR-130: KV Scheduler**
Scheduler must consider:
- KV-store as high priority (blocking future decode steps)  
- KV-load as global bottleneck  
- Per-core distribution for multi-head parallelism  
- DRAM/NoC availability

---

### **FR-140: KV ISA Generation**
1. KV_STORE_TILE instruction  
2. KV_LOAD_TILE instruction  
3. DRAM base and length must match tile metadata  
4. ISA sequences must preserve tile ordering and dependency

---

### **FR-150: NPU Runtime Execution**
1. DMA must issue DRAM read/write bursts per KV-store/load.  
2. DRAM controller handles:
   - bank-level queues  
   - row-buffer hit/miss  
   - burst alignment  
3. NoC must route KV packets.

---

### **FR-160: Profiling**
Profiler must record:
- KV-store time  
- KV-load time  
- DMA stalls  
- DRAM latency  
- NoC hop latency  
- Per-head timelines  
- Total attention latency breakdown

---

## 5.2 Non-Functional Requirements

### **NFR-10. Deterministic Execution**
Same KV workload → Same timeline.

### **NFR-11. Efficiency**
1 decode-step simulation < 4 seconds.

### **NFR-12. Flexibility**
KV layout pluggable module.

---

# 6. KPIs

| KPI | Target | Purpose |
|-----|--------|---------|
| KV-load latency accuracy | <10% | Validate memory model |
| DRAM BW usage | ±20% | Compare with analytic model |
| Stall attribution | 100% | No missing stall reason |
| KV tile coverage | 100% | All KV ops must be tiled |
| ISA correctness | 100% | Valid DRAM addresses |

---

# 7. Success Criteria

1. Simulator produces complete pipeline:
   - KV-store tiles  
   - KV-load tiles  
   - TileOpGraph  
   - Scheduled execution  
   - ISA (KV_STORE_TILE, KV_LOAD_TILE)  
   - Cycle-level timeline  

2. Profiler shows:
   - DRAM bandwidth usage  
   - NoC traffic  
   - KV-load stall hotspots  

3. Supports both:
   - Prefill (store-only)  
   - Decode (store + load)  

---

# 8. Future Extensions

- FlashAttention v2 KV tiling  
- Multi-layer KV interleaving  
- KV compression simulation  
- GQA per-group KV-cache  
- Sharded KV-cache across multiple NPU clusters  

---

# Appendix A: KV Tile Metadata

```
KvTileDesc:
    head_id
    time_start
    time_len
    d_start
    d_len
    dram_base_addr
    spm_required
    dtype_bytes
```

---

# Appendix B: ISA Requirements

```
KV_STORE_TILE:
    opcode,
    src_spm_addr,
    dram_base_addr,
    tile_size_bytes,
    flags

KV_LOAD_TILE:
    opcode,
    dram_base_addr,
    dst_spm_addr,
    tile_size_bytes,
    flags
```

---

# End of Document
