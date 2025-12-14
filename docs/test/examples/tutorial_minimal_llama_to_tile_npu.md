# From Minimal NumPy LLaMA to Tile-based NPU Modeling
## A Practical Tutorial for Understanding LLMs on NPUs

관련(메인 스펙 체크리스트):
- [tile_semantics_validation_checklist.md](../../spec/trace/tile_semantics_validation_checklist.md)

> 이 문서는 **NumPy로 구현한 가장 단순한 LLaMA**를 출발점으로,
> 이를 **타일 기반 NPU 관점(Tensor Engine / Vector Engine / SRAM / DRAM)**에서
> 어떻게 해석하고 성능 모델링까지 확장할 수 있는지를 단계적으로 설명한다.
>
> 정확한 사이클 시뮬레이터가 아니라,
> **“어디서 병목이 생기는가?”를 이해하고 설계 결정을 돕는 모델**이 목적이다.

---

## 1. 왜 NumPy 기반 LLaMA인가?

대부분의 LLM 구현은 PyTorch, CUDA, Triton 등 **하드웨어 세부를 감춘 추상화** 위에 있다.
그러나 NPU 설계/시뮬레이션 관점에서는 다음 질문에 답해야 한다.

- Attention의 어떤 부분이 **Matrix Engine**에서 실행되는가?
- Softmax / RMSNorm / RoPE는 **Vector/SFPU**에서 얼마나 비싼가?
- Prefill과 Decode의 병목이 왜 다른가?
- KV-cache는 **왜 DRAM 병목을 만든다**고 말하는가?

이를 이해하기 위해 이 프로젝트는:
- **NumPy로 LLaMA를 가장 직관적인 형태로 구현**
- 연산 의미(semantics)는 그대로 유지
- 그 위에 **타일 기반 비용 모델(instrumentation)**만 덧씌운다

---

## 2. 최소 LLaMA 구현 구조

### 2.1 전체 구조

```
Input Tokens
  ↓
Embedding
  ↓
[ Transformer Block × N ]
  ├─ RMSNorm
  ├─ Self-Attention
  │   ├─ Q/K/V projection
  │   ├─ RoPE
  │   ├─ QKᵀ → Softmax → P·V
  │   └─ Output projection
  └─ FFN (Gate / Up / Down)
  ↓
RMSNorm
  ↓
LM Head
```

이 구조는 **모든 LLaMA 계열의 공통 최소 골격**이다.

---

## 3. Attention을 NumPy로 가장 단순하게 표현하기

### 3.1 핵심 코드 (개념)

```python
score = np.einsum('...qhd,...khd->...hqk', q, k)
prob  = softmax(score / sqrt(d))
ctx   = np.einsum('...hqk,...khd->...qhd', prob, v)
```

이 3줄이 **Attention의 본질**이다.

하지만 NPU 관점에서는 다음처럼 해석된다:

| NumPy 연산 | NPU 관점 |
|-----------|---------|
| Q/K/V projection | Tensor Engine (GEMM) |
| QKᵀ | Tensor Engine (GEMM) |
| Softmax | Vector/SFPU (reduce + exp + div) |
| P·V | Tensor Engine (GEMM) |

---

## 4. Prefill vs Decode: 왜 병목이 다른가?

### 4.1 Prefill 단계

- 입력 길이 L이 큼
- Q, K, V 모두 길이 L
- 큰 행렬 곱 → **Compute-heavy**

```
Q: [L × D]
K: [L × D]
→ QKᵀ: [L × L]
```

➡️ **Matrix Engine 활용률이 핵심**

---

### 4.2 Decode 단계

- Q 길이 = 1
- K/V 길이 = 누적 토큰 수 t
- 매 스텝마다 KV-cache를 다시 읽음

```
Q: [1 × D]
K: [t × D]
```

➡️ **DRAM에서 KV-cache를 읽는 비용이 지배적**

이 차이 때문에:
- Prefill은 compute 최적화
- Decode는 **메모리 최적화(KV-cache 정책)**가 핵심이 된다.

---

## 5. KV-cache를 타일 기반으로 모델링하기

### 5.1 Pre-allocated KV-cache

Naive 구현:
```python
k = np.concatenate([k_cache, k_new], axis=1)
```

→ 매 decode마다 O(t²) 복사 발생

이 프로젝트에서는:
```python
cache["k"][:, cur:cur+L] = k_new
cache["cur"] += L
```

➡️ **실제 하드웨어와 유사한 KV append 모델**

---

### 5.2 KV Window (W)

Decode 시:
- 최근 W 토큰만 L1/SRAM에 상주
- 나머지는 DRAM에서 fetch

```
KV = [ cold (DRAM) | hot window (L1) ]
```

이것이:
- 실질적인 **mobile / edge NPU 설계 포인트**
- decode 성능을 좌우하는 핵심 파라미터

---

## 6. 타일 기반 비용 모델 (TileTracer)

### 6.1 TileSpec (하드웨어 추상화)

```python
TileSpec(
  T=32,
  dram_bw_GBps=40,
  l1_bw_GBps=600,
  fpu_TFLOPs=8,
  sfpu_TopS=1.5,
  noc_ports=4
)
```

이는:
- 특정 칩을 정확히 모델링하기보다는
- **“어떤 자원이 병목인가?”를 드러내는 스케일 모델**

---

### 6.2 GEMM / SFPU 이벤트

각 연산은 다음 이벤트로 기록된다:

- GEMM_TILE
  - DRAM bytes
  - L1 bytes
  - FLOPs
- SFPU_TILE
  - element count
  - ops

실행 시간은 단순화된 모델:

```
time = launch + max(memory_time, compute_time)
```

➡️ 정확한 사이클보다 **병목 위치 파악**이 목적

---

## 7. NoC / DRAM 컨텐션 모델

여러 head / 타일이 동시에 DRAM을 접근하면:

```
Effective BW = DRAM_BW / concurrency
```

- `noc_ports`로 최대 병렬 스트림 제한
- Decode에서 KV cold 접근에 적용

➡️ “왜 head 수가 늘면 decode가 느려지는가?”를 설명 가능

---

## 8. Stride 기반 KV cold 효율 (GQA / MQA)

### 8.1 문제

KV가 DRAM에 다음과 같이 배치되면:

- seq-major (연속) → 효율 좋음
- head-major interleaved → stride 큼 → 효율 나쁨

특히:
- GQA / MQA
- interleaved head layout
- 작은 KV window

➡️ **DRAM burst 효율 급락**

---

### 8.2 모델링 방법

DRAM 효율을 다음으로 근사:

```
effective_efficiency =
  size_based_efficiency(bytes)
× stride_penalty(stride_bytes)
```

stride는:
- head block 간 거리
- interleaved 정도로 근사

➡️ 주소 시뮬 없이도 **레이아웃 차이의 영향**을 정량화

---

## 9. FlashAttention 스타일 Prefill 모델

Prefill에서는:
- score(L×L)를 저장하지 않고
- K/V를 block 단위로 스트리밍

Softmax는 다음 SFPU 패스로 분해:

1. row max reduce
2. exp
3. row sum reduce
4. normalize

➡️ **Vector/SFPU 병목이 어디인지 명확히 드러남**

---

## 10. 자동 튜닝과 설계 탐색

이 시뮬레이터로 가능한 질문들:

- Decode가 DRAM-bound인가?
- KV window W는 얼마면 충분한가?
- Tile 크기 T는 prefill / decode에 각각 적절한가?
- KV 레이아웃을 바꾸면 성능이 얼마나 달라지는가?

이를 위해:
- T/W sweep
- DRAM-bound ratio 계산
- 자동 W 추천 로직 제공

---

## 11. 이 튜토리얼의 의의

이 문서는:
- “LLaMA가 어떻게 돌아가는지” 설명하는 문서가 아니다
- **“LLM이 NPU에서 왜 느려지는지”를 이해시키는 문서**다

특히:
- NPU 컴파일러
- SoC/NPU 아키텍처 설계
- 타일 기반 시뮬레이터
를 만드는 개발자를 위한 **실행 가능한 사고 도구**다.

---

## 12. 다음 단계

이 튜토리얼을 기반으로 다음 확장이 가능하다:

- 실제 NPU ISA로 lowering
- DMA / bank / row 모델 추가
- KV prefetch 스케줄링
- Energy 모델(J/op, J/byte)

이 레포는 **“정답을 주는 시뮬레이터”가 아니라
“설계 판단을 돕는 시뮬레이터”**를 목표로 한다.
