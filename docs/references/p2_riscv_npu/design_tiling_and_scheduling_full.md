
# Design: Tiling & Scheduling — IA_RISC_V_NPU_Simulator v2  
**Full Technical Design Document (Ultra‑Long Version)**

Version: 1.0  
Status: Complete  
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

이 문서는 **IA_RISC_V_NPU_Simulator v2**에서 핵심적인 두 축인  
**타일링(Tiling) 시스템**과 **스케줄링(Scheduling) 시스템**의 설계를 완전히 기술한다.

타일링과 스케줄링은 전체 시뮬레이터의 실행 효율과 정확도를 결정하는 가장 중요한 요소이며,  
본 문서에서는 다음을 명확히 정의한다:

- 타일 단위 데이터 구조  
- MatMul / Conv / Attention / KV-cache 타일 생성 규칙  
- 타일 기반 DAG(TileOpGraph) 구성 원칙  
- Static & Dynamic Scheduler 알고리즘  
- Core assignment 및 튜닝 포인트  
- Multi-core NPU 실행과 DRAM/NoC contention 반영방법  

---

# 1. Tiling System Overview

타일링은 다음 문제를 해결하기 위한 핵심 메커니즘이다:

1. SPM(scratchpad)에 데이터를 넣기 위한 메모리 블록 결정  
2. TE/VE 실행 가능한 granularity로 연산을 쪼개기  
3. DRAM 연속성(burst alignment)와 bank conflict 최소화  
4. 스케줄러가 타일 단위로 작업을 재배치할 수 있도록 단위화  
5. ISA generator가 tile-level 명령 생성 가능하도록 구조화  

모든 연산자는 **TileOpNodes**라는 타일 단위 DAG 노드로 표현된다.

---

# 2. TileDesc — 타일의 기본 단위

```
class TileDesc:
    tile_id: int
    tensor_id: int
    shape: Tuple[int]          # e.g., (M_tile, K_tile)
    offset: Tuple[int]         # starting index for slicing
    dram_base: int             # DRAM address
    dram_size: int             # in bytes
    spm_required: int          # SPM capacity required
    dtype_bytes: int
```

**불변 조건(Invariants):**

- 모든 타일의 dram_base/dram_size는 실제 tensor layout과 일치해야 한다.  
- spm_required ≤ SPM_total  
- tile shape이 텐서 범위를 벗어나면 안 된다.  

---

# 3. Tiling for Each Operator

이 절에서는 MatMul, Conv2D, Attention(Q/K/V), KV-cache의 타일링 설계를 다룬다.

---

# 3.1 MatMul Tiling

### 3.1.1 입력 형태  
`A: [M, K]`, `B: [K, N]`, output `C: [M, N]`

### 3.1.2 타일 구조  
```
for m in range(0, M, M_tile):
  for n in range(0, N, N_tile):
    for k in range(0, K, K_tile):
        create tile (m_block, n_block, k_block)
```

### 3.1.3 목적

- TE array에 맞는 tile 크기 구성  
- Data reuse 극대화  
- Partial sum C tile accumulate 지원  

### 3.1.4 pseudo-code

```
def tile_matmul(M, N, K, M_tile, N_tile, K_tile):
    tiles = []
    for m0 in range(0, M, M_tile):
        for n0 in range(0, N, N_tile):
            for k0 in range(0, K, K_tile):
                tile = TileDesc(
                    offset=(m0, n0, k0),
                    shape=(min(M_tile, M - m0),
                           min(N_tile, N - n0),
                           min(K_tile, K - k0))
                )
                tiles.append(tile)
    return tiles
```

---

# 3.2 Conv2D Tiling

### 3.2.1 출력 shape  
`[N, Cout, H_out, W_out]`

### 3.2.2 tiling axes  
- Cout axis blocking  
- H_out, W_out blocking  
- Cin blocking for SPM constraint  

### 3.2.3 stride/padding/dilation 반영  
슬라이딩 윈도우 접근을 통해 입력 좌표 계산.

---

# 3.3 Attention Tiling (Q/K/V)

### 3.3.1 입력 shape  
`Q, K, V: [B, H, T, D]`

### 3.3.2 tile axes  
- `H_tile` (head parallelism)  
- `T_tile` (sequence chunking)  
- `D_tile` (head dimension blocking)  

---

# 3.4 KV-cache Tiling

KV-cache는 v2 시뮬레이터에서 **최고 난이도 타일링**이다.

### 3.4.1 목적
- KV-store 타일 생성 (append mode)  
- KV-load 타일 생성 (range mode)  
- DRAM burst alignment 고려  
- Per-head memory layout 반영  

### 3.4.2 KV-store 타일링
```
for head in heads:
    dram_base = kv_base + head * head_stride + t * tile_stride
    create KV_STORE_TILE
```

### 3.4.3 KV-load 타일링  
범위 `[t0 … t1]`을 tile로 분할:

```
for t in range(t0, t1, T_tile):
    for d in range(0, D, D_tile):
        create KV_LOAD_TILE
```

### 3.4.4 Burst alignment  
각 tile은 DRAM을 burst_size N으로 정렬하여 분할.

---

# 4. TileOpGraph — 타일 단위 DAG

### 4.1 구조

```
class TileOpNode:
    id
    op_type
    input_tiles: List[TileDesc]
    output_tiles: List[TileDesc]
    deps: List[TileOpNode]
    est_compute_cycles
    est_mem_bytes
```

### 4.2 dependency 생성 규칙

- 같은 C tile에서 k-split partial sum은 순차적  
- MatMul → Softmax는 데이터 의존  
- KV-store → KV-load는 시간순  
- QKᵀ → Softmax → Attn·V → OutputProj 순서 유지  

---

# 5. Scheduling System Overview

스케줄러는 두 단계로 구성된다:

1. **Static Scheduler**  
2. **Dynamic Scheduler**

Static은 blueprint, Dynamic은 실제 실행.

---

# 6. Static Scheduler

## 6.1 목표

- 타일 DAG 기반 topological ordering  
- critical path 우선순위 부여  
- Multi-core coarse assignment  

## 6.2 알고리즘

### 6.2.1 단계 1 — Topological traversal
```
order = topo_sort(TileOpGraph)
```

### 6.2.2 단계 2 — Critical path 길이 계산
```
for node in reversed(order):
    node.cp = max(child.cp + node.cost, default=0)
```

### 6.2.3 단계 3 — Priority-based sorting
```
priority_queue = sort_by(node.cp)
```

### 6.2.4 단계 4 — Core assignment
라운드 로빈 또는 cost-aware 배분.

---

# 7. Dynamic Scheduler

Dynamic Scheduler는 **NPU 실행 중 발생하는 stall을 해결**하는 핵심 엔진이다.

## 7.1 고려 변수

- Core busy time  
- SPM buffer availability  
- DRAM / NoC busy 상태  
- 의존성 해결 여부  
- 타일의 mem/compute ratio  

---

## 7.2 메인 루프 pseudo-code

```
while not all_tiles_finished:
    for core in cores:
        core.update_current_tile()

    ready_tiles = tile_graph.update_ready_set()

    for core in idle_cores:
        best = select_best_tile(ready_tiles)
        core.run(best)

    dram.tick()
    noc.tick()
    profiler.tick()
```

---

# 8. Tile Selection Strategy

### 8.1 heuristic scoring

```
score(tile) =
    w1 * tile.cp_priority
  + w2 * tile.compute_intensity
  - w3 * expected_dram_stall
```

### 8.2 memory-bound 타일 우선  
KV-load, conv-in-load, QKᵀ-load 등을 먼저 실행하여 DRAM burst 생성.

---

# 9. Multi-Core Coordination

### 9.1 inter-core independence  
각 코어는 독립적 실행.

### 9.2 shared resource contention  
DRAM/NoC는 공유.

### 9.3 scheduling goals  
- head-parallelism 활용  
- time-parallelism 최소화  
- bank conflict 분산  

---

# 10. DRAM-Aware Scheduling

Dynamic scheduler는 DRAM 혼잡을 탐지하여:

- burst-aligned tile 우선  
- multi-head interleave  
- same-bank 반복 액세스 피하기  

---

# 11. SPM Allocation Model

타일 실행 전 SPM 공간 확보:

```
if spm_free >= tile.spm_required:
    allocate()
else:
    wait()
```

---

# 12. End-to-End Scheduling Example (LLaMA Attention)

```
Tiles:
  Q_proj tiles
  K_proj tiles
  V_proj tiles
  KV_STORE_TILE
  KV_LOAD_TILE range [0..t]
  QKᵀ matmul tiles
  Softmax tiles
  Attn·V tiles
  OutputProj tiles

Static:
  cp priority: QKᵀ > Softmax > AttnV > Proj

Dynamic:
  bursts timed with KV_LOAD
  multi-core assign
  timeline captured
```

---

# 13. Verification Rules

- 타일 DAG invariant: no cycle  
- DRAM 주소 정확성  
- SPM overflow 없음  
- 모든 타일 반드시 실행됨  
- compute/memory timeline이 ISA와 일치  

---

# 14. Testing Plan

- unit test: tile slicing, DRAM range calc  
- directed test: KV-load spanning 3 banks  
- integration test: LLaMA block  
- performance test: multi-core scaling  

---

# End of Document
