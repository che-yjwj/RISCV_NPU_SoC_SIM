
# Testing Strategy — IA_RISC_V_NPU_Simulator v2  
**Full Technical Document (Ultra‑Long Version)**  
Version: 1.0  
Status: Complete  
Author: IA_RISC_V_NPU_Simulator Team

---

# 0. Purpose

본 문서는 IA_RISC_V_NPU_Simulator v2의 **정확성, 안정성, 재현성, 아키텍처 일관성**을 보장하기 위한  
**테스트 전략(Test Strategy) 풀버전**이다.

Testing Strategy는 다음 목표를 가진다:

- ISA-level 시뮬레이션 정확성 보장  
- TE/VE/DMA/KV/NoC/DRAM 모델 간 동기/비동기 상호작용 검증  
- Tile lowering 규칙과 Tiling-Scheduler 간 일관성 검증  
- Cycle-based timeline의 재현성 검증  
- LLaMA Attention / FFN / Conv 등의 end-to-end correctness 확보  
- Regression 방지 및 자동화된 continuous validation 구축  

본 문서는 전체 테스트 플랜을 기술하며, 테스트 범위는 다음 레이어를 모두 포함한다:

```
Frontend (IR) → Tiler → Scheduler → Lowering → ISA Stream → Py‑V → NPU Runtime
```

---

# 1. Testing Layers Overview

다음 6개의 계층을 독립적으로, 그리고 교차적으로 테스트한다.

| Layer | Test Level | Description |
|-------|------------|-------------|
| 1. Tile-Level | Unit Test | TE/VE/DMA primitive correctness |
| 2. Lowering Rules | Unit/Integration | tile → ISA 변환 검증 |
| 3. Scheduler | Integration | DAG ordering, SPM lifetime, parallelism |
| 4. ISA Stream Execution | Integration | Py‑V + NPU Runtime tick-driven consistency |
| 5. Subgraph End-to-End | System | Attention, FFN, Conv2D |
| 6. Full Block/Model-Level | System/Golden | LLaMA block, full decode loop |

각 테스트는 다른 레이어와 독립적이며, 하나의 failure가 전체를 망치지 않도록 설계한다.

---

# 2. Tiered Testing Strategy (3단계 구조)

Testing은 다음 3단계로 구성된다.

## 2.1 Tier 1 — Primitive & Microkernel Validation  
**(Unit Test, 가장 작은 단위 검증)**

다음 요소를 단위로 검증한다:

- TE MatMul(FP16/Int8) reference vs simulator  
- VE Softmax / GELU / RMSNorm  
- DMA burst size, alignment, latency  
- KV_STORE_TILE DRAM append correctness  
- KV_LOAD_TILE range descriptor correctness  
- SPM allocation / boundary checking  
- NoC contention-free timing 모델  

의도는 “하나의 tile-level 연산이 reference와 동일한가?”이다.

---

## 2.2 Tier 2 — Subgraph & Pipeline Validation  
**(Integration Test, 여러 primitive의 조합)**

검증 대상:

- QKV Projection lowering → ISA correctness  
- Attention(QKᵀ→Softmax→AV) lowering correctness  
- FFN lowering correctness  
- Scheduler timeline validity  
- TE/VE/DMA 병렬 실행 타이밍 consistency  
- SYNC/FENCE 적용 위치 정확성  

모든 Subgraph-level 테스트는 아래 reference와 비교한다:

1. PyTorch reference (full-precision)  
2. Quantized PyTorch reference  
3. Simulator results (tile-based)  

---

## 2.3 Tier 3 — Full Block / Full Model  
**(System Test, golden dataset 기반)**

테스트 대상:

- Full LLaMA block correctness  
- Full decode-loop simulation consistency  
- KV-cache 성장(t 증가) 시 결과 안정성  
- End-to-end prompt → logits 출력 재현성  
- Cycle timeline monotonic scaling  
- Resource contention 시나리오 재현성  

이 단계는 실제 모델 구조를 테스트하므로 가장 긴 시간 소요.

---

# 3. Unit Tests (Tier 1 Detailed Plan)

## 3.1 TE/VE/DMA Primitive Tests

### TE MatMul Tile Test
- Random tile A, B 생성  
- Simulator output vs PyTorch matmul 비교  
- ACC-mode (partial sum) 포함  
- K-split accumulation 테스트  

### VE Tests  
- GELU approximate correctness  
- Softmax numerical stability  
- RMSNorm reference 대비 오차 검사  

### DMA Tests  
- DRAM address alignment test  
- Burst-length correctness  
- SPMregion boundary test  

---

## 3.2 KV Engine Tests

### KV_STORE_TILE Tests  
- head별 DRAM offset 증가 검사  
- timestep 증가 시 append 위치 확인  
- DRAM memory content compare  

### KV_LOAD_TILE Tests  
- kv_range_desc 테스트 (t_start, t_len)  
- DRAM → SPM tile correctness  
- multiple tiles load correctness  

---

# 4. Lowering Tests (Tile → ISA)

## 4.1 MatMul Lowering Tests

- A/B tile load order 검사  
- SYNC_WAIT insertion correctness  
- TE_MATMUL_TILE emission correctness  
- DMA_STORE_TILE correctness  

## 4.2 Attention Lowering Tests

- QKV lowering rules  
- KV_STORE lowering correctness  
- KV_LOAD lowering correctness  
- QKᵀ → Softmax → AV lowering consistency  

---

# 5. Scheduler Tests

Scheduler는 가장 오류가 많이 발생할 수 있는 영역이다.

### 검증 항목:

1. DAG Topology Validity  
2. SPM lifetime correctness  
3. tile eviction-free guarantee  
4. TE/VE 병렬성 보장  
5. DMA–Compute overlap  
6. NoC contention 모델 consistency  
7. SYNC/FENCE ordering correctness  

### 타임라인 기반 테스트

시뮬레이터의 timeline을 dump하여 reference timeline과 비교:

```
timeline_ref.json
timeline_sim.json
```

latency / concurrency / order consistency 검사.

---

# 6. ISA Execution Tests (Py‑V + NPU Runtime)

ISA 스트림 실행은 다음 3 요소를 포함한다:

- Py‑V MMIO / CSR / doorbell  
- NPU Runtime tick loop  
- TE/VE/DMA/KV/NoC tick pipeline  

### ISA Execution Test Categories

1. **Single-tile execution**  
2. **Tile chain execution**  
3. **KV-store + KV-load execution**  
4. **QKᵀ + Softmax + AV**  
5. **Output projection**  
6. **Full attention**  

각 단계에서 DRAM/SPM snapshot diff를 통해 correctness 판정.

---

# 7. End-to-End Tests

## 7.1 Attention End-to-End Test

- X → QKV → KV-store → KV-load → QKᵀ → Softmax → AV → OutProj  
- PyTorch reference 대비 tile recomposition output 비교  

## 7.2 FFN End-to-End Test

- MatMul(W1) → GELU → MatMul(W2)  
- PyTorch result 비교  

## 7.3 Full LLaMA Block

- 입력 X에 대한 block output(Y) 비교  
- FP16 reference와의 deviation 수치 리포트  

## 7.4 Decode-loop Test

t = 0..127 동안:

- KV-cache growth  
- KV-load 증가  
- attention latency 증가 패턴  
- logits output reference 비교  

---

# 8. Stress Tests

다음 극단적 조건에서 simulator robustness 검증:

- 매우 큰 t (e.g., t=2048)  
- 매우 작은 tile size  
- SPM overflow 시나리오  
- DMA bandwidth=low 제한 모델  
- TE/VE latency 갈등  
- NoC congestion heavy 모드  

각 stress case는 crash 없이 결과를 내야 한다.

---

# 9. Regression Tests

PR/commit마다 자동으로 실행:

- TE/VE unit tests  
- Lowering tests  
- Scheduler DAG tests  
- ISA execution tests  
- E2E attention/FFN tests  

pytest + GitHub Actions + deterministic random seed 사용.

---

# 10. Logging & Debugging Infrastructure

테스트 실패 시 아래 로그들이 자동 저장됨:

- tile metadata dump  
- lowering log  
- ISA stream dump  
- cycle timeline dump  
- DRAM/SPM memory snapshot  
- Py‑V instruction trace  
- contention model trace  
- KV-cache map snapshot  

이는 debugging efficiency 향상을 위해 핵심적이다.

---

# 11. Metrics to Validate

테스트는 correctness뿐 아니라 다음 metric도 포함한다:

- latency monotonicity  
- memory bandwidth consistency  
- TE/VE/DMA utilization  
- tile reuse ratio  
- KV-load scaling curve  
- NoC hop-count fairness (optional)  

---

# 12. Coverage Goals

| Category | Coverage Goal |
|----------|----------------|
| TE/VE primitive | >95% |
| Lowering rules | >90% |
| Scheduler path | >85% |
| ISA execution | >95% |
| End-to-end attention | 100% |
| Decode-loop | 100% |

---

# End of Document
