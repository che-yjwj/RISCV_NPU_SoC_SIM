# Prefill / Decode 워크로드 매핑 명세
(Prefill / Decode Workload Mapping Specification)

## 1. 문서 목적

본 문서는 타일 기반 NPU 아키텍처에서 LLM 추론의 두 단계인 Prefill과 Decode 워크로드를
어떻게 타일 단위로 분해하고,
Tensor Engine(TE), Vector Engine(VE), Global SRAM, Shared Tile Buffer(STB)에
매핑할 것인지를 정의한다.

본 명세는 다음 문서들을 전제로 한다.

- Tile Lifecycle Specification
- Memory Hierarchy Specification
- Compute Engines Specification
- TE–VE Dataflow & Interface Semantics Specification

본 문서의 목적은 Prefill과 Decode를
동일한 아키텍처 구조 위에서,
서로 다른 스케줄링 및 데이터 이동 패턴으로 실행하도록
아키텍처 수준에서 고정하는 데 있다.

---

## 2. Prefill과 Decode의 아키텍처적 차이

### 2.1 Prefill의 성격

Prefill은 다음 특성을 가진다.

- 입력 시퀀스 길이 S가 큼
- Attention score 행렬이 S × S 형태
- 대규모 GEMM과 높은 병렬성
- 연산 집약도(compute intensity)가 높음

Prefill의 최적화 목표는 처리량(throughput)이다.

---

### 2.2 Decode의 성격

Decode는 다음 특성을 가진다.

- 한 스텝에 1 token 처리
- KV cache 길이 T가 점진적으로 증가
- Attention은 Q(1) × K(T) 형태
- 메모리 트래픽(KV load)이 지배적

Decode의 최적화 목표는 지연(latency)이다.

---

## 3. 공통 전제: 레이어의 타일 기반 분해

Transformer의 각 레이어는 다음과 같이 엔진 책임으로 분해된다.

### 3.1 Tensor Engine (TE)

- Q/K/V Projection
- QKᵀ 계산
- P·V 계산
- Output Projection
- FFN (FC1, FC2)

### 3.2 Vector Engine (VE)

- LayerNorm (mean / variance reduction)
- Softmax (max / sum reduction)
- Activation (GELU, SiLU 등)
- Residual add, scaling, clipping

### 3.3 Global SRAM과 STB의 역할

- Global SRAM
  - 모든 타일의 저장 및 재사용
  - Prefill / Decode 공통의 데이터 허브
- Shared Tile Buffer(STB)
  - TE 결과 타일을 VE로 전달하는 스트림 경계
  - 디스크립터 기반 handoff

---

## 4. Prefill 워크로드 매핑

### 4.1 Prefill 한 레이어의 타일 흐름

1. LayerNorm (VE)
   - 입력 X 타일을 Global SRAM에 두고 VE에서 LN 수행
   - 결과 X_norm 타일을 Global SRAM에 기록

2. Q/K/V Projection (TE)
   - X_norm 타일과 가중치 타일을 사용해 TE에서 GEMM 수행
   - Q, K, V 타일 생성
   - K, V는 KV cache로 DRAM에 저장
   - 동시에 Global SRAM에도 상주 가능

3. QKᵀ (TE) → Softmax (VE)
   - TE가 score tile(Sq_tile × Sk_tile) 생성
   - score tile을 Global SRAM에 기록
   - STB를 통해 score tile 디스크립터 전달
   - VE가 Global SRAM에서 score tile을 읽어 softmax 수행
   - softmax 결과 P tile을 Global SRAM에 기록

4. P·V 및 후처리
   - TE가 P tile과 V tile을 사용해 output tile 생성
   - 이후 projection, FFN은 TE 중심
   - Activation, Residual, LN은 VE에서 수행

---

### 4.2 Prefill에서 Global SRAM의 핵심 역할

- Score tile과 P tile은 DRAM으로 저장해서는 안 된다
- TE ↔ VE 간 반복 소비가 발생하므로
  Global SRAM 상주와 STB handoff가 필수이다

Prefill 성능은 다음 요소에 의해 결정된다.

- Global SRAM의 동시 타일 수용 능력
- TE/VE 파이프라인 중첩 정도
- STB back-pressure 발생 빈도

---

### 4.3 Prefill 스케줄링 원칙

- Score tile은 생성 직후 즉시 Softmax에 소비되도록 배치
- 타일 생산과 소비가 인접한 파이프라인 유지
- 목적은 Global SRAM 점유 피크 감소와 TE/VE 동시 활용 극대화이다

---

## 5. Decode 워크로드 매핑

### 5.1 Decode에서의 구조적 변화

Decode에서는 다음이 근본적으로 달라진다.

- Q는 1 token
- K, V는 KV cache에서 반복 로드
- Attention은 메모리 트래픽 지배

Decode는 데이터 이동 중심 워크로드이다.

---

### 5.2 Decode 한 레이어의 타일 흐름

1. LayerNorm (VE)
   - 입력 X(1 token)를 VE에서 LN 수행
   - 결과 X_norm 생성

2. QKV Projection (TE)
   - 소형 GEMM으로 Q, K_new, V_new 생성
   - K_new, V_new는 DRAM의 KV cache에 append
   - 필요 시 Global SRAM에 staging

3. KV Cache 타일 로드 (DMA)
   - K_cache를 head 또는 group 단위 타일로 분할
   - DRAM에서 Global SRAM으로 스트리밍 로드
   - TE/VE 소비 속도에 맞춘 prefetch 큐 유지

4. QKᵀ (TE) → Softmax (VE)
   - Q(1)과 K_tile(Tk)로 score tile(1 × Tk) 생성
   - STB를 통해 score tile 디스크립터 전달
   - VE가 softmax 수행
   - T가 길 경우 reduction multi-pass 발생 가능

5. P·V 누산 (TE)
   - P tile과 V_tile을 사용해 partial output 누산
   - 모든 K/V 타일 순회 후 최종 output 생성

---

### 5.3 Decode에서의 주요 병목 요소

시뮬레이터는 다음을 반드시 관측 가능해야 한다.

- KV cache DRAM → Global SRAM DMA 대역폭
- Global SRAM bank contention
- STB back-pressure로 인한 TE stall
- VE softmax reduction의 lane utilization 저하

---

## 6. Prefill과 Decode의 연결: KV Cache

- KV cache는 Prefill 단계에서 생성된다
- Prefill에서 생성된 K, V는 DRAM에 저장된다
- Decode는 이를 반복적으로 로드하여 사용한다

Decode 성능은 KV cache 접근 패턴에 의해 지배되므로,
Global SRAM은 KV cache의 on-chip staging buffer 역할을 수행한다.

---

## 7. STB의 활용 위치 비교

STB는 두 단계 모두에서 핵심적이다.

- Prefill
  - QKᵀ score tile → Softmax
- Decode
  - Q(1) × K(T) score tile → Softmax

Attention 경로에서 STB는 필수 구조 요소이다.
TE가 생성한 타일이 VE에 전달될 때는 **최소 1회 STB handoff**가 발생해야 하며,
VE 내부에서 동일 타일을 반복 소비할 때는
STB 재경유 없이 글로벌 SRAM 재사용이 허용된다.

---

## 8. 시뮬레이터 반영을 위한 최소 실행 모델

### 8.1 공통 이벤트

- dma_load(tile_id, DRAM → GlobalSRAM)
- dma_store(tile_id, GlobalSRAM → DRAM)
- te_compute(tile_ids)
- stb_push(tile_desc)
- stb_pop()
- ve_compute(tile_id)
- tile_free(tile_id)

---

### 8.2 Prefill 워크로드 생성 규칙

- 루프 구조
  - layer → sequence tile → head 또는 group
- Score tile 생성 후 즉시 softmax 소비
- TE/VE 파이프라인 유지가 목표

---

### 8.3 Decode 워크로드 생성 규칙

- 루프 구조
  - layer → time step
- KV tile은 선prefetch 후 소비
- DMA, TE, VE가 중첩 실행되도록 정적 스케줄링
- head/group 당 **prefetch 큐 깊이 2타일 이상**을 기본값으로 생성
- 동시 상주 KV 타일 수는 Global SRAM 용량 내에서 2~3개로 제한하여
  스케줄러가 해제 이벤트를 명시적으로 모델링하도록 한다

---

## 9. Prefill / Decode 비교 지표

시뮬레이터는 다음 지표를 산출해야 한다.

- DRAM bytes / token
- Global SRAM peak occupancy
- TE utilization과 VE utilization
- STB stall rate
- VE lane utilization (reduction tail)
- DRAM-bound vs compute-bound 판정

---

## 10. 요약

- Prefill은 연산 중심, Decode는 메모리 중심 워크로드이다
- 두 단계는 동일한 타일 기반 아키텍처 위에서
  서로 다른 스케줄링과 데이터 이동 패턴으로 실행된다
- Global SRAM과 STB는 Prefill과 Decode 모두에서 핵심 축이다
- 이 매핑이 고정되어야 시뮬레이터의 성능 분석 결과가 의미를 가진다
