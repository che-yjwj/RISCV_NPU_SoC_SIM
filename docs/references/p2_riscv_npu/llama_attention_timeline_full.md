
# LLaMA Attention Timeline — IA_RISC_V_NPU_Simulator v2  
**Full Technical Example (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
Author: IA_RISC_V_NPU_Simulator Team

---

# 0. Purpose

본 문서는 LLaMA Self-Attention 연산을  
**타일 단위 실행 시간축(Time‑Axis Timeline)**으로 전개하여  
IA_RISC_V_NPU_Simulator v2가 생성하는  
**Gantt-style pipeline timeline**의 개념적 완전 버전을 설명한다.

이 문서는 다음을 보여준다:

- DMA / TE / VE / KV ISA 간 병렬성  
- SPM tile lifetime  
- KV-store vs KV-load ordering  
- Softmax dependency barrier  
- Output projection까지의 전체 latency 흐름  
- timestep 증가(t) 기반 attention latency scaling  

---

# 1. Components Modeled in the Timeline

Timeline에는 다음 5개 execution domain이 존재한다:

| Domain | 의미 |
|--------|------|
| **DMA** | DRAM ↔ SPM 전송 (LOAD/STORE/KV_LOAD/KV_STORE) |
| **TE** | MatMul, QKᵀ, Attn·V |
| **VE** | Softmax, RMSNorm, GELU |
| **KV Engine** | KV-store append, KV-load range aggregation |
| **SYNC / FENCE** | dependency 보장 구간 |

각 domain은 서로 독립적인 파이프라인을 가지며,  
특정 순간에 여러 domain이 동시에 실행될 수 있다.

---

# 2. Example Scenario Metadata

예시는 다음 조건을 가정한다:

- timestep t = 5  
- KV-cache 크기: K_all/V_all tile fetch cost 증가  
- TE(MatMul/QKᵀ/AV) latency > VE  
- DMA bandwidth: TE와 동시 실행 가능  
- tile 메모리 크기: 64×64 FP16 tile  

또한 다음 SPM buffer mapping을 사용한다:

```
spmX    = 0x01
spmQ    = 0x02
spmK    = 0x03
spmV    = 0x04
spmKall = 0x05
spmVall = 0x06
spmScore= 0x07
spmO    = 0x08
```

---

# 3. Timeline Legend

```
[ DMA ]  : DMA operation running
[ TE  ]  : Tensor Engine compute
[ VE  ]  : Vector Engine compute
[ KV  ]  : KV-store or KV-load operation
[SYNC]  : dependency fence
```

병렬성 표현:

```
DMA:  |----A----|
TE :        |------B------|
VE :                 |--C--|
```

---

# 4. LLaMA Attention Timeline (Conceptual Gantt Chart)

아래는 timestep t=5에서 한 attention step이 어떻게 실행되는지 보여주는  
**full pipeline timeline**이다.

```
Time →
┌──────────────────────────────────────────────────────────────────────────────┐
│                             1. QKV Projection                               │
└──────────────────────────────────────────────────────────────────────────────┘
DMA:   |---Load X---|      |--Load Wq--|              |--Load Wk--|            |--Load Wv--|
TE :                   |-----MatMul(X,Wq)-----|          |-----MatMul(X,Wk)-----|   |-----MatMul(X,Wv)-----|
KV :                                                                                    
VE :                                                                                    
SYNC:        [SYNC]                                  [SYNC]                        [SYNC]

┌──────────────────────────────────────────────────────────────────────────────┐
│                             2. KV Cache Store                                │
└──────────────────────────────────────────────────────────────────────────────┘
DMA:   
KV :                                |--KV_STORE(K_t)--| |--KV_STORE(V_t)--|
SYNC:                                                    [Group Sync]

┌──────────────────────────────────────────────────────────────────────────────┐
│                             3. KV Load (Range Fetch)                         │
└──────────────────────────────────────────────────────────────────────────────┘
DMA:                                           |-----------KV_LOAD(K_all)-----------|
KV :                                           |-----------KV_LOAD(V_all)-----------|
SYNC:                                                                 [SYNC]

┌──────────────────────────────────────────────────────────────────────────────┐
│                             4. Attention Scores (QKᵀ)                         │
└──────────────────────────────────────────────────────────────────────────────┘
TE :                                                           |------QKᵀ------|
SYNC:                                                                   [SYNC]

┌──────────────────────────────────────────────────────────────────────────────┐
│                                     5. Softmax                              │
└──────────────────────────────────────────────────────────────────────────────┘
VE :                                                                       |--Softmax--|
SYNC:                                                                                 [SYNC]

┌──────────────────────────────────────────────────────────────────────────────┐
│                                6. Attn·V Multiplication                      │
└──────────────────────────────────────────────────────────────────────────────┘
TE :                                                                                |------AV------|
SYNC:                                                                                        [SYNC]

┌──────────────────────────────────────────────────────────────────────────────┐
│                                7. Output Projection                           │
└──────────────────────────────────────────────────────────────────────────────┘
DMA:                                                                                      |--Load Wout--|
TE :                                                                                               |----MatMul(O,Wout)----|
DMA:                                                                                                            |--Store Out--|
```

핵심 특징:

### ✔ QKV projection 동안 DMA와 TE가 깊게 overlap  
### ✔ KV-store는 TE/VE와 독립적으로 즉시 실행됨  
### ✔ KV-load는 DMA longest dependency를 만들어 attention latency 증가  
### ✔ QKᵀ → Softmax → AV는 순차적 dependency  
### ✔ Output projection은 Softmax 이후 재병렬화가 가능  

---

# 5. Timeline with SPM Lifetime Visualization

```
SPM Buffer      Lifetime
-----------------------------------------------------------
spmX     |====Loaded=====|======Used in Q,K,V======|
spmQ                       |====Q produced=====|     | used in QKᵀ |
spmK                             |====K produced=====|     | used/store |
spmV                                   |====V produced=====| |store|
spmKall                                             |======KV-load=====| |used in QKᵀ|
spmVall                                              |=====KV-load=====|           |used in AV|
spmScore                                                          |QKᵀ|--Softmax--|
spmO                                                                             |---AV---|
spmY                                                                                      |OutProj|
```

이 시각화는 Scheduler가 다음을 최적화할 때 핵심이다:

- tile lifetime 최소화  
- SPM eviction cost 방지  
- TE/VE concurrency 극대화  

---

# 6. Timeline-Based Latency Analysis

### Latency Sources

| Stage | Latency 영향 요인 |
|--------|---------------------|
| QKV Projection | Weight DMA + 3 MatMuls |
| KV-Store | DRAM write bandwidth |
| KV-Load | **t에 비례** (sequence grows) |
| QKᵀ | TE latency, K_all tile 크기 증가 |
| Softmax | VE latency |
| Attn·V | TE latency |
| Output projection | Weight DMA + MatMul |

---

# 7. Attention Latency Scaling with Timestep t

KV-load와 QKᵀ의 tile grid 크기는 timestep t 증가에 따라 증가한다.

### KV-load 증가:
```
t=0  → no KV range, direct K_t only  
t=5  → 6 tiles  
t=100 → ~101 tiles  
t=1000 → ~1001 tiles
```

### QKᵀ tile grid 증가:
```
tile_count ∝ t * (D / D_tile)
```

### 결과:
```
Attention latency ∝ O(t)
```

시뮬레이터는 해당 scale을 정확히 반영한다.

---

# 8. Summary

본 문서에서는 다음을 완전히 설명했다:

- LLaMA attention의 tile-level execution timeline  
- TE/VE/DMA/KV domain 간 concurrency 관계  
- SYNC barrier의 영향  
- tile lifetime 시각화  
- timestep 증가에 따른 latency scaling  

이 타임라인 문서는 end-to-end attention ISA 문서와 Scheduler 설계 문서의  
중간 레이어 역할을 한다.

---

# End of Document
