<!-- status: draft -->

# PRD: IA_RISC_V_NPU_Simulator v2

## Version
1.0 (Full Specification)

## 0. Document Purpose
This Product Requirements Document (PRD) defines the full functional and non-functional requirements for **IA_RISC_V_NPU_Simulator v2**, a research-grade, end‑to‑end NPU architecture simulator spanning IR → tiling → scheduling → ISA → RISC‑V host → NPU execution → DRAM/NoC contention → profiling.

This simulator targets transformer/LLM workloads (e.g., LLaMA, Qwen, Mistral), CNNs, and embedding-heavy systems.

---

# 1. Problem Statement

Modern AI accelerators must execute:
- Tile-level MatMul-heavy kernels
- Memory-bound decoder attention
- KV-cache intensive workloads
- Irregular embedding access patterns

However, *existing simulation tools* fail to provide:
- Tile-level execution modeling
- KV-cache append/load accuracy
- DRAM/NoC contention behavior
- End-to-end flow (IR → ISA → timeline)
- Multi-core NPU behavior
- Interaction between RISC-V host CPU and NPU command queues

Therefore, a new unified simulator is required.

---

# 2. Goals

## 2.1 Functional Goals
**FG-1. End-to-End AI Workload Simulation**
- From PyTorch/ONNX/DSL to IR → Tiling → Scheduling → ISA → NPU → profiling.

**FG-2. Tile-Level Execution Modeling**
- TE/VE analytic compute.
- DMA + DRAM/NoC cycle-level modeling.

**FG-3. KV-cache First-Class Support**
- KV-store append
- KV-load range access
- Time-step decoder modeling

**FG-4. LLaMA Attention Latency Analysis**
- Break down latency into:
  - Q/K/V projection
  - KV-store/load
  - QKᵀ matmul
  - Softmax
  - Attn·V
  - Output projection
  - DRAM/NoC delays

**FG-5. Multi-Core NPU Model**
- Tile scheduling across multiple cores
- Shared DRAM/NoC contention

---

## 2.2 Non-Functional Goals

**NFG-1. Accuracy**
- DRAM bandwidth error < 15%
- Decoder-step latency error < 10% vs analytic model

**NFG-2. Extensibility**
- New ISA instructions can be added
- New tilers (FlashAttention, grouped-query attention)
- New DRAM models (HBM, LPDDR)

**NFG-3. Developer-Friendly**
- Modular code
- Clear PRD/TDD separation
- All components replaceable (tiler, scheduler, DRAM model)

---

# 3. Non-Goals

- RTL-accurate timing simulation  
- Electrical/thermal simulation  
- Real RISC-V OS booting  
- Cycle-accurate out‑of‑order CPU simulation (Py‑V is simplified)  

---

# 4. Use Cases

## UC-1. LLaMA Attention Analysis
Simulate:
- Q/K/V projection tile behavior
- KV-cache DRAM load/store pressure
- Per-head traffic imbalance
- Multi-core overlap behavior

## UC-2. KV-store / KV-load Latency Study
- Prefill = store only
- Decode = store + multi-range load patterns
- DRAM burst alignment effects

## UC-3. MatMul / Conv2D Benchmarking
- Compare tile shapes, SPM sizes, number of cores

## UC-4. Embedding Workload Simulation
- Index trace-based embedding fetch
- DRAM locality evaluation

## UC-5. NPU Design Space Exploration
- TE array width/height
- VE width
- SPM size
- DRAM bandwidth
- NoC topology

---

# 5. Requirements

## 5.1 Functional Requirements (FR)

### **FR-001: Frontend**
- PyTorch FX importer
- ONNX importer
- DSL-to-IR converter

### **FR-010: IR Processing**
- Canonicalization
- Fusion patterns
- Shape inference
- Dead code elimination

### **FR-020: Tiling**
- MatMul tiler (M/N/K tiling)
- Conv2D tiler
- Attention tiler (Q/K/V tiles)
- KV-cache tiler (range-based)
- SPM-aware tile validation

### **FR-030: Scheduler**
- Static scheduler (topological + critical path)
- Dynamic scheduler (runtime resource‑aware)
- Multi-core scheduling support

### **FR-040: ISA Generator**
- 64-bit xNPU ISA
- TE/VE/DMA/SYNC/CONFIG opcodes
- KV_STORE_TILE / KV_LOAD_TILE support
- Per-core ISA stream builder

### **FR-050: Py‑V Host Simulation**
- RISC‑V CPU
- NPU command queue + doorbell
- Completion queue
- CSR/MMIO modeling

### **FR-060: NPU Execution Engine**
- TE pipeline analytic model
- VE analytic model
- DMA engine execution
- SPM buffer allocation
- Core tick loop

### **FR-070: DRAM/NoC Model**
- DRAM channel/bank queue
- Row-buffer model
- NoC arbitration
- Burst size handling

### **FR-080: KV-cache**
- KvDescTable required
- KV-store append
- KV-load with [t0, t1] range
- Per-head layout control

### **FR-090: Profiling**
- Per-cycle timeline event logging
- TE/VE/DMA utilization
- DRAM/NoC bandwidth chart
- Tile-level latency breakdown

---

## 5.2 Non-Functional Requirements (NFR)

### **NFR-1. Performance**
- Simulate 1 LLaMA attention step < 3 seconds on modern CPU
- Full layer simulation < 30 seconds

### **NFR-2. Modularity**
- Each module (IR, tiler, scheduler, ISA, NPU, DRAM) replaceable

### **NFR-3. Determinism**
- Given identical inputs, outputs must be bitwise identical

### **NFR-4. Traceability**
- All decisions (tile generation, scheduling, lowering, memory mapping)
  must be trackable from IR → timeline.

---

# 6. KPIs

| KPI | Target | Description |
|-----|--------|-------------|
| **Latency Accuracy** | < 10% | LLaMA attention decode-step |
| **DRAM BW accuracy** | < 15% | Compare with analytic or reference model |
| **Tile Coverage** | 100% | All IR ops decomposed into tiles |
| **ISA Consistency** | 100% | All tiles lower to ISA without loss |
| **Repeatability** | deterministic | cycle timeline reproducible |

---

# 7. Success Criteria

1. LLaMA attention example produces complete:  
   - tile list  
   - tile graph  
   - scheduled tile order  
   - ISA stream  
   - cycle-accurate timeline

2. DRAM/NoC contention patterns visible in profiling.

3. KV-cache behavior validated:  
   - append-store  
   - range-load  
   - per-head DRAM traffic

4. Simulator modularity proven by swapping:  
   - tiling algorithm  
   - scheduler  
   - DRAM model  
   - NPU core configuration  

---

# 8. Future Extensions

- FlashAttention-style tiling and scheduler integration  
- Multi‑layer attention KV locality predictor  
- Multi‑chip NoC for large NPU clusters  
- Power/perf co‑simulation model  
- Auto-tiling search (RL-based or heuristic search)  

---

# 9. References

- Meta LLaMA Architecture Papers  
- MLPerf Inference (Mobile/Edge)  
- NVIDIA CUTLASS / cuBLASLt tiling methods  
- Research on KV-cache locality and memory bottlenecks  
- EONSim, PyTorchSim, ONNXim  

---

# Appendix A. Glossary

- **Tile:** smallest schedulable compute or memory unit  
- **TileOpNode:** dependency-aware tile-level IR op  
- **SPM:** on-chip scratchpad memory  
- **KV-cache:** key/value memory region for decoder transformer  
- **Py‑V:** RISC-V simulator used as host CPU  
- **xNPU ISA:** custom 64-bit instruction set for NPU operations  
