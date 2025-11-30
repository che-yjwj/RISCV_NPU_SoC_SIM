<!-- status: draft -->

# IA_RISC_V_NPU_Simulator v2  
**High-Fidelity, Modular, Research-Grade RISC‑V + NPU Architecture Simulator**  
**Full README.md (Ultra‑Long Version)**  

---

## 🚀 Introduction

IA_RISC_V_NPU_Simulator v2는 **PyTorch/ONNX/DSL → IR → Tiling → Scheduling →  
xNPU ISA → RISC‑V Host → NPU Runtime → DRAM/NoC → Timeline**에 이르는  
전체 AI/LLM 워크로드를 시뮬레이션하는 **풀스택 NPU 시뮬레이터**입니다.

Transformer/LLM 기반 워크로드(LLaMA, Qwen, Mistral 등)의 **KV-cache 중심 디코딩 병목**,  
MatMul/Conv 중심의 대규모 연산 패턴, DRAM/NoC 병목, multi-core 병렬 실행 등  
현대 NPU 아키텍처의 전체적인 성능 요구사항을 정확하게 분석할 수 있도록 설계되었습니다.

본 README는 전체 프로젝트의 개념·구성·흐름·기능·설치를  
아주 상세하게 설명한 **완전체(Long-form) 문서**입니다.

---

# 🧠 1. Key Philosophy

### ✔ 분석적 Compute + Cycle-level Memory
- TE/VE compute: analytic latency 모델  
- DRAM/NoC: cycle-level contention 모델  
- Memory—특히 KV-load—가 latency를 지배하는 현실 반영  

### ✔ Tile-Centric Architecture
- 모든 연산은 **TileOpNode** 단위로 구성  
- 타일은 scheduler/ISA/DRAM 모델을 잇는 기본 단위  

### ✔ End-to-End Consistency
IR → Tiles → TileOpGraph → ISA → Timeline  
모든 단계가 완전히 일관된 정보를 유지한다.

---

# 🏗️ 2. System Architecture

```mermaid
flowchart TD
    A[PyTorch / ONNX / DSL] --> B[Frontend Normalizer]
    B --> C[IRGraph]
    C --> D[Tiling Engine]
    D --> E[TileOpGraph<br>Dependency Builder]
    E --> F[Scheduler<br>(Static + Dynamic)]
    F --> G[xNPU ISA Generator]
    G --> H[RISC-V Py‑V Host]
    H --> I[NPU Command Queue]
    I --> J[NPU Runtime<br>(TE/VE/DMA/SPM)]
    J --> K[DRAM + NoC Model]
    K --> J
    J --> L[Profiler / Timeline / Utilization]
```

---

# 🧩 3. Module Overview

## 3.1 Frontend
- PyTorch FX → IR 변환  
- ONNX → IR 변환  
- DSL → IR Compiler  
- Normalization, Canonicalization, Fusion 패스 포함  

---

## 3.2 IR System
- `IRNode` (MatMul, Conv2D, LN, Softmax, KVStore, KVLoad 등)  
- Shape inference, Dead code pruning  
- Pattern fusion (QKV, FFN 등)  

---

## 3.3 Tiling System
타일은 다음 정보를 포함:

```
TileDesc {
    tensor_id
    offset
    shape
    dram_base
    dram_size
    spm_required
}
```

### 지원 타일링
- MatMul (M/N/K 차원 블록)  
- Conv2D (Cout/H/W/Cin)  
- Q/K/V Attention tiles  
- **KV-cache store / load tiles** (range 기반)  

---

## 3.4 TileOpGraph
타일 단위 DAG 생성:

- MatMul partial-sum dependency  
- Attention QKᵀ → Softmax → Attn·V → OutputProj  
- KV-store → KV-load dependency  

---

## 3.5 Scheduler

### Static Scheduler
- critical-path 기반  
- topological 정렬  
- coarse core assignment  

### Dynamic Scheduler
- DRAM/NoC 상태 기반 실시간 tile dispatch  
- DMA stall, bank conflict, SPM 부족 고려  

---

## 3.6 xNPU ISA 시스템
64-bit 명령어 구조:

- DMA_LOAD_TILE  
- DMA_STORE_TILE  
- TE_MATMUL_TILE  
- VE_OP_TILE  
- **KV_STORE_TILE**  
- **KV_LOAD_TILE**  
- SYNC, CONFIG  

---

## 3.7 Py-V Host CPU
- NPU 명령 스트림 제출  
- doorbell & MMIO 기반 실행  
- completion queue polling  

---

## 3.8 NPU Runtime
**Per-core 엔진:**
- TE (Tensor Engine)  
- VE (Vector Engine)  
- DMA Engine  
- SPM Allocator  

**Compute → Memory → Compute** 순환 구조를 cycle-wise로 업데이트.

---

## 3.9 DRAM + NoC Model
- DRAM channels / banks / row-buffer  
- FR-FCFS arbitration  
- RW-switching 페널티  
- NoC packet routing  
- Bandwidth saturation modeling  

---

## 3.10 KV-cache Engine
Transformer decoder에서 핵심:

- KV-store append (per-head DRAM layout)  
- KV-load range fetch  
- Burst alignment  
- KV tile slicing  

---

## 3.11 Profiler
- TE/VE/DMA timeline  
- DRAM bank timeline  
- NoC traffic heatmap  
- Tile-level latency breakdown  
- Layer-level summary  

---

# 🔍 4. LLaMA Attention End-to-End Example

### Complete flow:

1. Q/K/V projection tile 생성  
2. K_t, V_t KV-store  
3. 모든 기존 KV range 값 KV-load  
4. QKᵀ tile matmul  
5. Softmax  
6. Attn·V  
7. Output projection  
8. Timeline & stall breakdown  

Timeline 예시는 다음과 같다:

```
Core0: | DMA | ---- TE ---- | VE |
Core1:        | DMA | TE | ---- DMA ---- |
DRAM: |RRR|WW|RRRRR|W|
NoC: congestion ↑
```

---

# 🧪 5. Installation & Usage

## 5.1 Install

```bash
git clone https://github.com/.../IA_RISC_V_NPU_Simulator_v2
cd IA_RISC_V_NPU_Simulator_v2
pip install -r requirements.txt
```

---

## 5.2 Run LLaMA Example

```bash
python scripts/run_llama_attention_example.py
```

---

# 📂 6. Directory Structure (Expanded)

```
.
├── src/
│   ├── frontend/
│   ├── ir/
│   ├── tiler/
│   ├── scheduler/
│   ├── isa/
│   ├── pyv/
│   ├── npu_core/
│   ├── memory_noc/
│   ├── kv_embedding/
│   └── viz/
│
└── docs/
    ├── prd/
    ├── design/
    ├── isa/
    ├── examples/
    └── overview/
```

---

# 📊 7. Profiling Output Examples

- **Timeline Gantt Chart**  
- **Per-core utilization**  
- **KV-load stall heatmap**  
- **DRAM bandwidth graph**  
- **NoC link occupancy**  

---

# 🧬 8. Extensibility Roadmap

- FlashAttention tiling  
- Grouped-query attention  
- Multi-chip NoC  
- HBM bandwidth scaling  
- Auto-tiling RL optimizer  
- MLIR frontend  

---

# ✨ 9. Why This Simulator Matters

현대 NPU 설계는 compute FLOPS만 보고 판단할 수 없다.  
실제 병목은:

- DRAM bandwidth  
- KV-cache memory locality  
- NoC routing delay  
- tile scheduling & DRAM arbitration  
- TE/VE stall time  

이 시뮬레이터는 “왜 성능이 나오는지/안 나오는지”를 tile-level로 분석한다.

---

# 📜 10. License & Contribution

### Contributions welcome
Fork → PR → Review → Merge

### License
TBD

---

# 🙌 11. Contact

For questions, collaboration, research discussions:  
Open GitHub Issues or email the maintainers.

---

# End of README.md
