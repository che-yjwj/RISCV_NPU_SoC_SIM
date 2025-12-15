# TileRT Analysis (Reference, Research Track)

**Path:** `docs/design/tile_rt_analysis.md`  
**Status:** Reference  
<!-- status: reference -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

본 문서는 TileRT(Tile-based Runtime)의 개념/철학을 요약하고,
이를 **타일 기반 시뮬레이터(결정론적 global-cycle + TE/VE 결정론적 compute)** 설계에
어떻게 흡수할 수 있는지에 대한 참고(Reference) 정리이다.

주의:
- 메인 스펙(SSoT)은 `docs/spec/*`이며, 본 문서는 규범을 고정하지 않는다.

---

## 2. TileRT의 문제의식

### 2.1 기존 LLM 추론 런타임의 한계
기존 LLM 런타임(vLLM 등)은 다음 전제를 기반으로 설계되어 있다.

- 최적화 목표: Throughput(tokens/sec)
- 실행 단위: Operator / Layer
- 스케줄링 단위: Batch
- Prefill / Decode 단계 분리

이 구조는 **Batch=1, 실시간 응답, 모바일/엣지 환경**에서는 근본적인 비효율을 야기한다.

### 2.2 TileRT의 관점 전환
TileRT는 LLM 추론을 다음과 같이 재정의한다.

> LLM 추론은 연산 그래프 실행 문제가 아니라,
> **Latency Critical DAG Scheduling 문제**이다.

이를 위해 Layer 단위 실행을 해체하고, **Tile 단위 실행과 지연 최소화 스케줄링**을 도입한다.

---

## 3. TileRT의 핵심 추상화: Tile

### 3.1 Tile 정의
Tile은 단순한 블록이 아니라, 실행의 최소 단위이다.

```
Tile = {
  Compute Subgraph,
  Tensor Slice,
  Explicit Dependency,
  Latency Cost Model
}
```

Tile은 다음을 포함할 수 있다.
- GEMM의 부분 블록
- Attention의 QK 타일
- Softmax 타일
- KV-cache Load/Store 타일

연산, 메모리 이동, 통신을 **동일한 실행 객체**로 취급한다는 점이 핵심이다.

---

## 4. TileRT 전체 파이프라인

```
[Model Graph]
      ↓
[Tile Decomposition]
      ↓
[Tile Dependency DAG]
      ↓
[Latency-aware Scheduler]
      ↓
[Runtime Execution Engine]
      ↓
[HW Backend (GPU / NPU)]
```

핵심 구성 요소는 다음과 같다.

- **Tile Decomposer**: 연산 그래프를 타일 DAG로 분해
- **Tile DAG**: Fine-grained 의존성 표현
- **Latency-aware Scheduler**: Critical Path 최소화
- **Runtime Engine**: 타일 단위 실행 및 자원 할당

---

## 5. TileRT Scheduler의 특성

### 5.1 스케줄링 목표
TileRT 스케줄러의 목적 함수는 다음과 같다.

```
minimize (Time_to_First_Token + Tail Latency)
```

Throughput이 아닌 **지연(latency)**이 최우선 목표이다.

### 5.2 실행 전략
- Dependency가 없는 Tile은 즉시 실행
- Compute / DMA / Vector 연산을 적극적으로 중첩
- Decode 단계의 serial dependency gap 최소화

Attention decode 시 KV load, QK GEMM, Softmax, V GEMM이 **pipeline 형태로 얽혀 실행**된다.

---

## 6. Prefill / Decode 재정의

기존 개념:
- Prefill: Batch 병렬
- Decode: Token-by-token 직렬

TileRT 관점:
- Prefill / Decode 구분은 의미 없음
- 둘 다 Tile DAG 실행 문제

| 항목 | Prefill | Decode |
|---|---|---|
| DAG 길이 | 김 | 짧음 |
| 병렬성 | 높음 | 낮음 |
| Scheduler | 동일 | 동일 |

---

## 7. NPU 시뮬레이터 관점에서의 TileRT 적용

### 7.1 NPU-IR 확장 제안
기존 NPU-IR 연산자 중심 모델을 다음과 같이 확장한다.

```
TILE_OP {
  tile_id
  op_type
  tensor_slice
  dependency_ids
  est_compute_cycles
  est_mem_cycles
}
```

IR은 명령어가 아니라 **스케줄링 객체**가 된다.

---

### 7.2 Cycle-based 시뮬레이터 매핑

전역 CPU cycle loop 기반 시뮬레이터에 TileRT를 다음과 같이 매핑한다.

```
Global Cycle Loop:
  - Ready Tile Queue
  - Dependency Counter Update
  - HW Resource Availability Check
  - Tile Dispatch
  - Tile Retire
```

- 명령어 retire → Tile retire
- Gantt chart를 Tile 단위로 시각화 가능

---

### 7.3 TE / VE / DMA 매핑

| Tile 유형 | 실행 유닛 |
|---|---|
| GEMM Tile | Tensor Engine (TE) |
| Vector / Softmax Tile | Vector Engine (VE) |
| KV Load/Store Tile | DMA |

Heterogeneous NPU 구조와 자연스럽게 정합된다.

---

## 8. TileRT가 던지는 아키텍처적 질문

1. NPU는 명령어 기반이어야 하는가, Tile Task 기반이어야 하는가?
2. DMA와 Compute를 동일 스케줄링 레벨에서 다룰 수 있는가?
3. KV-cache는 메모리인가, 파이프라인의 일부인가?

TileRT의 답은 명확하다.

> **모든 것은 Tile이다.**

---

## 9. 한계와 현실적 고려사항

- Tile DAG 관리 오버헤드
- Tile granularity tuning 난이도
- HW latency 모델 정확도 요구
- 디버깅 및 검증 복잡성 증가

제품화에는 부담이 크지만, **연구·시뮬레이터·아키텍처 탐색에는 매우 강력**하다.

---

## 10. 단계별 적용 로드맵

### 단기
- TileDesc 기반 NPU-IR 확장
- Tile-level Gantt chart 시각화
- KV Load / Compute 통합 스케줄링

### 중기
- Prefill/Decode 통합 Tile Scheduler
- Tile dependency 기반 Stall 분석
- JSON trace 기반 Critical Path 분석

### 장기
- Tile-first NPU ISA
- Command Queue → Tile Queue 전환
- Dynamic / Chaos 기반 실행 모델과 결합

---

## 11. 핵심 요약

TileRT는 LLM 추론을 **연산 중심 실행 모델에서 지연 최소화 DAG 스케줄링 문제로 재정의**한 접근이며, NPU 시뮬레이터 및 NPU-IR과 결합할 때 그 가치가 극대화된다.

본 문서는 TileRT를 연구 및 시스템 설계에 흡수하기 위한 기준 문서로 활용될 수 있다.
