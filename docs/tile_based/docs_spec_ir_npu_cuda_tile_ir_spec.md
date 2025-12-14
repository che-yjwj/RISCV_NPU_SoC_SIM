# NPU Tile IR Spec

본 문서는 **Tile-centric NPU Simulator**의 핵심 중간 표현(IR)을 정의한다.
NPU Tile IR은 하드웨어 독립적인 **Virtual ISA** 역할을 수행한다.

---

## 1. Tile IR의 위치

```
ONNX
 ↓
Graph Normalize
 ↓
Tile IR   ← 핵심 계층
 ↓
Lowering (TE / VE / DMA)
 ↓
NPU ISA
 ↓
Simulator
```

Tile IR은 하드웨어 세부 사항을 은닉하며, Tile Contract를 전제로 동작한다.

---

## 2. Tile IR 설계 원칙

1. 모든 연산은 Tile 단위로 표현된다.
2. Scalar / element-wise 연산은 존재하지 않는다.
3. 메모리는 주소가 아닌 **Tile ID**로 참조된다.
4. 모든 의존성은 명시적으로 표현된다.
5. Tile Contract를 절대 위반하지 않는다.

---

## 3. Tile IR Core Instruction Set

### 3.1 Compute Operations

```
GEMM_T(A_tile, B_tile) -> C_tile
VEC_ADD_T(A_tile, B_tile) -> C_tile
LNORM_T(X_tile, gamma, beta) -> Y_tile
SOFTMAX_T(X_tile) -> Y_tile
```

---

### 3.2 Memory Operations

```
LOAD_TILE(DRAM_addr) -> Tile
STORE_TILE(Tile) -> DRAM_addr
```

- LOAD/STORE는 Tile 단위로만 수행된다.
- DRAM 접근은 Memory Op로만 허용된다.

---

### 3.3 Synchronization & Dependency

```
WAIT_TILE(tile_id)
BARRIER(tile_group)
```

- Tile IR은 암묵적 순서를 갖지 않는다.
- 모든 실행 순서는 dependency graph로 결정된다.

---

## 4. Tile Dependency Graph (TDG)

Tile IR은 DAG 형태의 실행 그래프로 표현된다.

```
LOAD A ─┐
        ├─ GEMM ─→ LNORM ─→ STORE
LOAD B ─┘
```

TDG는 다음의 입력으로 사용된다.

- Static Scheduler
- Timeline / Gantt 시각화
- 병목 분석 및 utilization 분석

---

## 5. Tile IR의 불변성과 확장성

| 변경 가능 요소 | 불변 요소 |
|---|---|
| Tile size | Tile op 의미 |
| TE latency | Tile dependency |
| DMA BW | Tile lifetime |
| VE pipeline | Tile DAG |

Tile IR은 하드웨어 세대가 바뀌어도 유지된다.

---

## 6. IR Summary

- Tile IR은 Virtual ISA이다.
- Scheduler와 Simulator는 Tile IR을 기준으로 동작한다.
- 모든 성능 분석의 기준은 Tile 단위이다.

