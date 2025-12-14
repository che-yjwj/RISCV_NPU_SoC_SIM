# KV Cache 타일링 전략 명세
(KV Cache Tiling Strategy Specification)

## 1. 문서 목적

본 문서는 타일 기반 NPU 아키텍처에서
LLM 추론 시 사용되는 **Key/Value Cache(KV cache)** 를
어떤 기준으로 타일링하고,
Global SRAM 및 연산 엔진에 어떻게 매핑해야 하는지를 정의한다.

본 명세는 다음을 목표로 한다.

- Prefill과 Decode 단계 모두에서 일관된 KV cache 구조 유지
- Decode 단계에서의 DRAM 접근 최소화
- Vector Engine 및 Tensor Engine의 타일 처리 효율 극대화
- GQA(Grouped Query Attention), MQA(Multi-Query Attention),
  그리고 interleaved heads 구조를 아키텍처적으로 고정

본 문서는 구현 기법이나 최적화 트릭을 설명하지 않으며,
**허용되는 구조와 허용되지 않는 구조를 명확히 구분하는 규범 문서**이다.

---

## 2. KV Cache의 역할과 기본 전제

### 2.1 KV Cache의 역할

KV cache는 다음을 저장한다.

- 과거 time step에서 생성된 Key 벡터
- 과거 time step에서 생성된 Value 벡터

KV cache는 Decode 단계에서
현재 Query와 반복적으로 결합되어 Attention 연산을 수행하는
**장기 메모리 구조**이다.

---

### 2.2 KV Cache에 대한 기본 전제

- KV cache는 **DRAM에 영속적으로 저장**된다
- Decode 단계에서 KV cache는 반복적으로 로드된다
- KV cache는 연산 결과가 아닌 **연산 입력 데이터**이다
- KV cache는 타일 단위로만 Global SRAM에 staging된다

KV cache 전체를 온칩에 상주시켜서는 안 된다.

---

## 3. KV Cache의 기본 차원 구조

KV cache는 다음 차원 구조를 가진다.

- Time dimension (T)
- Head 또는 Group dimension (H 또는 G)
- Head dimension (Dh)

KV cache는 시간 축(T)을 따라 계속 증가하며,
Decode 성능은 이 축을 따라 발생하는 데이터 이동 비용에 의해 지배된다.

---

## 4. KV Cache 타일링의 기본 원칙

KV cache 타일링은 다음 원칙을 반드시 따른다.

1. 타일링의 1차 기준은 **Time dimension**이다
2. KV cache는 **연속된 시간 구간** 단위로 타일링된다
3. 타일은 Global SRAM에 staging된 후 소비된다
4. 소비가 끝난 타일은 즉시 해제된다
5. KV cache 타일은 재사용되지 않는다

KV cache 타일은 “저장 자산”이 아니라
“스트리밍 입력”으로 취급된다.

---

## 5. MQA (Multi-Query Attention) 타일링 전략

### 5.1 MQA의 구조적 특성

MQA에서는 다음이 성립한다.

- Query head 수 > Key/Value head 수
- 모든 Query head가 **동일한 K/V를 공유**한다

이 구조는 KV cache 메모리 사용량을 최소화하는 대신,
K/V 로드 패턴의 효율성이 중요해진다.

---

### 5.2 MQA 타일링 규칙

- KV cache는 head 차원에서 **타일링하지 않는다**
- 타일은 다음 형태를 가진다.
  - [Time_tile × Dh]
- 하나의 KV 타일은 모든 Query head에서 재사용된다

MQA에서는 KV 타일 재사용이 허용되며,
이는 Global SRAM에서만 발생해야 한다.

---

### 5.3 MQA에서의 허용 구조

- KV 타일을 Global SRAM에 로드
- 여러 Query head가 동일 KV 타일을 순차적으로 소비
- 소비 완료 후 KV 타일 해제

다음 구조는 허용되지 않는다.

- Query head마다 KV 타일을 중복 로드하는 구조
- KV 타일을 STB를 통해 전달하는 구조

---

## 6. GQA (Grouped Query Attention) 타일링 전략

### 6.1 GQA의 구조적 특성

GQA에서는 다음이 성립한다.

- Query head는 여러 그룹(G)으로 묶인다
- 각 그룹은 하나의 K/V head를 공유한다
- Query head 수 > K/V head 수

GQA는 MQA와 Multi-Head Attention(MHA)의 중간 형태이다.

---

### 6.2 GQA 타일링 규칙

- KV cache는 **Group 단위로 분리**된다
- 타일은 다음 형태를 가진다.
  - [Group × Time_tile × Dh]
- 하나의 KV 타일은 동일 Group 내 Query head에서만 재사용된다

Group 경계를 넘는 KV cache 재사용은 허용되지 않는다.

---

### 6.3 GQA에서의 허용 구조

- Group 단위 KV cache를 DRAM에 저장
- Decode 시 Group별로 KV 타일을 Global SRAM에 staging
- 동일 Group의 Query들이 해당 KV 타일을 소비

다음 구조는 허용되지 않는다.

- Group을 무시한 KV cache flatten
- Query head별 KV cache 복제

---

## 7. Interleaved Heads 타일링 전략

### 7.1 Interleaved Heads의 목적

Interleaved heads 구조는 다음을 목표로 한다.

- DRAM burst 효율 향상
- Global SRAM bank conflict 감소
- Vector Engine lane utilization 개선

이를 위해 head 또는 group 차원을
메모리 상에서 **교차(interleave)** 배치한다.

---

### 7.2 Interleaved Heads 배치 규칙

- KV cache는 다음 순서로 메모리에 배치된다.
  - (Time_tile, Head_or_Group, Dh)
- 연속된 메모리 주소에는
  - 서로 다른 head 또는 group의 KV 데이터가 교차 배치된다

이 배치는 Decode 단계에서
연속적인 DMA burst 로드를 가능하게 한다.

---

### 7.3 Interleaving의 한계

Interleaving은 다음 범위를 넘지 않아야 한다.

- Time_tile 경계는 절대 넘지 않는다
- Group 경계를 넘는 interleaving은 허용되지 않는다
- Global SRAM bank 구조를 무시한 interleaving은 금지된다

Interleaving은 메모리 접근 최적화 수단이지,
논리적 구조 변경 수단이 아니다.

---

## 8. KV Cache와 연산 엔진의 상호작용

### 8.1 Tensor Engine 관점

- KV cache는 Tensor Engine의 입력 데이터이다
- QKᵀ 연산 시 KV 타일은 반복적으로 소비된다
- KV 타일은 연산 결과가 아니므로 STB를 통과하지 않는다

---

### 8.2 Vector Engine 관점

- Softmax 연산은 QKᵀ 결과 타일에만 적용된다
- KV cache 자체는 Vector Engine의 직접 입력이 아니다
- VE는 KV cache 타일의 배치와 크기에 영향을 받는다

---

## 9. Decode 단계에서의 KV Cache 로드 스케줄링

Decode 단계에서는 다음 스케줄링 규칙을 따른다.

- KV 타일은 계산보다 먼저 prefetch 된다
- Global SRAM에는 소수의 KV 타일만 상주한다
- 소비가 끝난 KV 타일은 즉시 해제된다
- KV 타일 로드와 QKᵀ 계산은 중첩 실행된다

KV cache 로드는 파이프라인의 일부이지,
독립된 단계가 아니다.

---

## 10. 금지된 KV Cache 구조

다음 구조는 아키텍처적으로 허용되지 않는다.

- KV cache 전체를 Global SRAM에 상주시켜 사용하는 구조
- Query head마다 KV cache를 중복 저장하는 구조
- KV cache를 STB를 통해 전달하는 구조
- Time dimension을 무시한 무작위 KV 접근
- Prefill과 Decode에서 서로 다른 KV cache 레이아웃 사용

---

## 11. 시뮬레이터 구현에 대한 요구 사항

올바른 시뮬레이터는 다음을 반드시 모델링해야 한다.

- KV cache의 Time 기반 타일링
- GQA/MQA에 따른 KV 타일 재사용 규칙
- Interleaved heads에 따른 DRAM burst 패턴 차이
- KV 타일의 Global SRAM staging 및 즉시 해제
- KV cache 로드가 성능 병목으로 작용하는 구간

KV cache는 단순한 배열이 아니라,
Decode 성능을 결정하는 핵심 구조로 취급되어야 한다.

---

## 12. 요약

- KV cache는 DRAM에 존재하는 장기 입력 데이터이다
- KV cache 타일링의 기준 축은 Time dimension이다
- MQA는 최대 재사용, GQA는 제한적 재사용을 허용한다
- Interleaved heads는 메모리 접근 효율을 위한 배치 전략이다
- KV cache는 스트리밍 입력이며, 저장 대상이 아니다

이 규칙이 고정되지 않으면,
Decode 단계의 성능 분석과 아키텍처 비교는 의미를 잃는다.
