# Tile Contract Spec

본 문서는 **RISC-V 기반 Tile-centric NPU Simulator**를 위한 HW–SW 경계 계약(Contract) 문서이다.
본 계약은 컴파일러, 런타임, 시뮬레이터, 하드웨어 모델 모두가 **반드시 준수해야 하는 불변 규칙**을 정의한다.

---

## 1. 목적

Tile Contract는 다음을 명확히 고정한다.

- IR / 컴파일러가 **보장해야 하는 조건**
- TE / VE / DMA / SPM 하드웨어가 **가정하는 전제**
- 시뮬레이터가 **절대 위반해서는 안 되는 규칙**

> Tile Contract는 파라미터 튜닝 대상이 아니라 **아키텍처의 헌법**이다.

---

## 2. Tile의 정의

Tile은 연산, 메모리, 스케줄링의 최소 공통 단위이다.

```
Tile = { Data Region, Compute Shape, Lifetime }
```

- 모든 연산은 Tile 단위로만 표현된다.
- Scalar 또는 element-wise 연산 개념은 IR에 존재하지 않는다.

---

## 3. Tensor Engine (TE) Tile Contract

### 3.1 TE Tile Shape (고정 계약)

| 항목 | 값 (예시) | 비고 |
|---|---|---|
| M | 32 | Output rows |
| N | 32 | Output cols |
| K | 32 | Reduction |
| Input Type | INT8 / FP16 / BF16 | ISA 고정 |
| Accumulator | INT32 / FP32 | 고정 |

- IR은 위 shape을 **변경 불가 상수**로 가정한다.
- 다른 크기의 연산은 여러 tile의 조합으로만 표현 가능하다.

---

### 3.2 TE Tile Memory Contract

```
SPM Layout (example)
+--------------------+
| A_tile (MxK)       |
| B_tile (KxN)       |
| C_tile (MxN)       |
+--------------------+
```

- Tile 데이터는 SPM에 연속적으로 배치된다.
- DMA는 tile 단위 burst fetch/store를 수행한다.
- Compute 단계에서 DRAM 접근은 허용되지 않는다.

---

### 3.3 TE Tile Execution Contract

```
[DMA Load] → [TE Compute] → [DMA Store]
```

- Tile 내부 실행은 atomic 하다.
- Tile 단위 preemption은 허용되지 않는다.
- 병렬성은 tile 간 수준에서만 허용된다.

---

## 4. Vector Engine (VE) Tile Contract

### 4.1 VE Tile Shape

| 항목 | 값 |
|---|---|
| Vector Length | 128 / 256 |
| Supported Ops | ADD, MUL, FMA, EXP, RSQRT |
| Reduction | Tree-based |

LayerNorm, Softmax는 VE tile 연산의 조합으로 구성된다.

---

### 4.2 VE Tile Memory Contract

- 입력 tile은 SPM 또는 Global SRAM에 존재한다.
- 출력 tile은 DRAM을 거치지 않고 TE tile 입력으로 직접 전달될 수 있다.

---

## 5. DMA Tile Contract

| 항목 | 규칙 |
|---|---|
| Transfer Granularity | Tile |
| Burst Size | Tile size 이상 |
| Overlap | Double-buffer 허용 |
| Ordering | Tile order 유지 |

---

## 6. Tile Lifetime Contract

```
ALLOC → LOAD → COMPUTE → STORE → FREE
```

Scheduler는 tile lifetime을 기준으로 다음을 계산한다.

- SPM capacity pressure
- DMA contention
- TE / VE utilization

---

## 7. Contract Summary

- Tile은 하드웨어가 기대하는 최소 실행 단위이다.
- IR과 Scheduler는 Tile Contract를 위반할 수 없다.
- 모든 성능 모델과 타이밍 모델은 Tile 단위로 계산된다.

