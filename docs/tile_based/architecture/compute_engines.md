# 연산 엔진 명세 (Compute Engines Specification)

## 1. 문서 목적

본 문서는 타일 기반 NPU 아키텍처에서 사용되는 **연산 엔진(Compute Engine)** 의
역할, 책임 경계, 입력·출력 관계를 정의한다.

이 문서는 연산 엔진의 내부 마이크로아키텍처, 파이프라인 단계, 명령어 포맷을 정의하지 않으며,
대신 **각 엔진이 무엇을 해야 하고, 무엇을 해서는 안 되는지**를 명확히 고정한다.

본 명세의 목적은 Tensor Engine과 Vector Engine의 역할 혼합을 방지하고,
타일 기반 데이터 흐름이 붕괴되지 않도록 설계를 고정하는 데 있다.

---

## 2. 연산 엔진의 분류

본 아키텍처는 다음 두 종류의 연산 엔진을 가진다.

- Tensor Engine (TE)
- Vector Engine (VE)

이 두 엔진은 **성능 특성, 처리 대상, 데이터 접근 방식**이 근본적으로 다르며,
서로 대체될 수 없다.

---

## 3. Tensor Engine (TE)

### 3.1 Tensor Engine의 정의

Tensor Engine은 **고밀도 행렬 연산**을 담당하는 연산 엔진이다.

Tensor Engine은 다음 연산 유형을 처리한다.

- 행렬 곱셈 (GEMM)
- 대규모 누산(MAC) 기반 연산
- 구조적으로 규칙적인 2차원 연산

---

### 3.2 Tensor Engine의 책임

Tensor Engine은 다음 책임을 가진다.

- 2차원 타일(2D tile)의 생성
- 높은 산술 집약도(arithmetic intensity)를 갖는 연산 수행
- 연속적이고 예측 가능한 데이터 접근 패턴 유지

Tensor Engine의 연산 결과는 **타일 단위로 생성**된다.

---

### 3.3 Tensor Engine의 입력과 출력

- 입력:
  - 글로벌 SRAM에 상주하는 타일
- 출력:
  - 글로벌 SRAM에 기록된 타일
  - 또는 Shared Tile Buffer를 통한 타일 handoff

Tensor Engine은 DRAM에 직접 접근하지 않는다.

---

### 3.4 Tensor Engine이 하지 않는 일

Tensor Engine은 다음을 수행하지 않는다.

- Reduction 중심 연산
- Softmax, LayerNorm과 같은 통계 기반 연산
- 비정형 제어 흐름을 포함한 연산
- 타일 라이프사이클 관리

---

## 4. Vector Engine (VE)

### 4.1 Vector Engine의 정의

Vector Engine은 **벡터 기반 후처리 및 정규화 연산**을 담당하는 연산 엔진이다.

Vector Engine은 다음 연산 유형을 처리한다.

- Element-wise 연산
- Reduction 연산
- Normalization 연산
- Activation 함수

---

### 4.2 Vector Engine의 책임

Vector Engine은 다음 책임을 가진다.

- 1차원 또는 축소된 형태의 타일 처리
- Reduction을 포함하는 다단계 연산 수행
- 타일 기반 반복 처리

Vector Engine의 연산은 반드시 **타일 단위로 수행**된다.

---

### 4.3 Vector Engine의 입력과 출력

- 입력:
  - Shared Tile Buffer를 통한 타일 참조
  - 글로벌 SRAM에 상주하는 타일 데이터
- 출력:
  - 글로벌 SRAM에 기록된 타일

Vector Engine은 DRAM에 직접 접근하지 않는다.

---

### 4.4 Vector Engine이 하지 않는 일

Vector Engine은 다음을 수행하지 않는다.

- 대규모 2D 행렬 곱셈
- 고산술 집약도 MAC 연산
- 타일 생성의 주체 역할
- 글로벌 SRAM의 소유 또는 관리

---

## 5. Tensor Engine과 Vector Engine의 역할 분리 원칙

Tensor Engine과 Vector Engine은 다음 원칙에 따라 분리된다.

- Tensor Engine은 **생산자(producer)** 중심
- Vector Engine은 **소비자(consumer)** 중심
- 하나의 타일은 TE에서 생성되고 VE에서 후처리된다
- 두 엔진은 동일한 연산을 중복 수행하지 않는다

역할 분리가 유지되지 않으면,
타일 기반 파이프라인은 구조적으로 붕괴된다.

---

## 6. 엔진 간 데이터 전달 원칙

- Tensor Engine과 Vector Engine 사이의 데이터 전달은
  반드시 Shared Tile Buffer를 통해 이루어진다
- 전달 대상은 타일 디스크립터이다
- 타일 데이터는 항상 글로벌 SRAM에 존재한다

엔진 간 직접 메모리 소유권 이전은 허용되지 않는다.

---

## 7. 금지된 연산 엔진 사용 패턴

다음 사용 패턴은 아키텍처적으로 허용되지 않는다.

- Tensor Engine에서 Softmax 또는 LayerNorm을 수행하는 행위
- Vector Engine에서 대규모 GEMM을 수행하는 행위
- 하나의 엔진이 타일의 생성과 소비를 동시에 담당하는 행위
- 엔진 내부 로컬 버퍼를 통해 타일을 공유하는 행위
- 연산 엔진이 타일 라이프사이클을 직접 관리하는 행위

---

## 8. 시뮬레이터 구현에 대한 요구 사항

올바른 시뮬레이터는 다음을 만족해야 한다.

- Tensor Engine과 Vector Engine을 명확히 분리된 컴포넌트로 모델링
- 두 엔진의 연산 유형이 겹치지 않도록 강제
- 엔진 간 데이터 전달을 STB 이벤트로 모델링
- 엔진이 글로벌 SRAM의 소유권을 갖지 않도록 보장

엔진 내부 파이프라인의 상세 모델링은 선택 사항이다.
엔진의 **책임 경계 위반은 허용되지 않는다**.

---

## 9. 요약

- Tensor Engine은 타일을 생성한다
- Vector Engine은 타일을 소비하고 정제한다
- 두 엔진은 역할이 겹치지 않는다
- Shared Tile Buffer는 엔진 간 연결 지점이다

이 역할 분리가 유지될 때만,
타일 기반 NPU 아키텍처는 예측 가능하고 확장 가능한 구조를 유지할 수 있다.
