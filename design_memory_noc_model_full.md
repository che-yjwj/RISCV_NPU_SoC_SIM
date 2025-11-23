
# Design: Memory & NoC Model — IA_RISC_V_NPU_Simulator v2  
**Full Technical Design Document (Ultra-Long Edition)**  
Version: 1.0  
Status: Complete  
Author: IA_RISC_V_NPU_Simulator Team  

---

# 0. Purpose

이 문서는 **IA_RISC_V_NPU_Simulator v2**에서  
**메모리(Memory) 계층과 NoC(Network-on-Chip) 모델**을 정확하게 시뮬레이션하기 위한  
전체 설계 상세를 정의한다.

본 문서의 목표는 다음이다:

- DRAM/NoC 병목을 정확하게 포착  
- KV-cache 의존 워크로드의 메모리 지배적 특성 반영  
- Multi-core NPU에서 발생하는 shared-resource contention 모델링  
- DMA burst, bank conflict, row-buffer behavior를 현실에 가깝게 추상화  
- 타임라인 프로파일링과 stall attribution을 명확히 제공  

---

# 1. System Overview

Memory & NoC subsystem은 다음 요소로 구성된다.

```
NPU Core DMA Engine
        ↓
     NoC Router
        ↓
DRAM Controller
        ↓
 DRAM Channels
        ↓
 DRAM Banks
```

각 요청(Request)은 다음 단계를 거쳐 처리된다:

1. DMA가 DRAM 요청 생성  
2. 요청 → NoC로 전달 (packet단위)  
3. 패킷이 DRAM controller queue로 들어감  
4. bank-level arbitration  
5. row-buffer hit/miss 계산  
6. burst-size만큼 실제 전송  
7. 데이터가 NoC를 통해 반환  
8. DMA가 SPM으로 write  

본 시뮬레이터는 memory-bound attention workload를 정확히 처리하기 위해  
특히 KV-load/store의 burst 단위 traffic과 DRAM scheduling behavior를 정교하게 모델링한다.

---

# 2. DRAM Model Overview

## 2.1 DRAM Structure

```
DRAM
 ├── Channel[0..C-1]
 │    ├── Bank[0..B-1]
 │    │    ├── Row buffer
 │    │    ├── Bank queue
 │    │    └── Timing state
 │    ├── Channel Arbiter
 │    └── Read/Write queues
```

---

## 2.2 Key Timing Parameters

본 시뮬레이터는 다음을 추상화한 단순화된 타이밍을 사용한다:

| Timing Parameter | Meaning |
|-----------------|----------|
| tBURST          | Burst 전송 시간 |
| tBANK_HIT       | 동일 row hit 시 delay |
| tBANK_MISS      | 다른 row 접근 시 row-buffer 교체 비용 |
| tCH_SWITCH      | R↔W 전환 페널티 |
| tNOC_LAT        | NoC 왕복 latency (hop 기반) |

---

## 2.3 DRAM Request

```
class DRAMRequest:
    addr: int
    size: int
    rw: READ or WRITE
    core_id
    tile_id
```

각 요청은 tile-based DMA burst를 기반으로 생성된다.

---

# 3. DRAM Address Mapping

## 3.1 Mapping Strategy

기본 DRAM 주소 매핑:

```
addr → channel, bank, row, col
```

### Default (row-major) mapping:
```
channel = (addr / CH_STRIDE) % NUM_CHANNELS
bank    = (addr / BK_STRIDE) % NUM_BANKS
row     = (addr / ROW_SIZE)
col     = addr % ROW_SIZE
```

## 3.2 Burst alignment rule

DMA tile은 항상 `burst_size` 단위로 DRAM에 정렬하여 접근한다:

```
aligned_addr = (addr // burst_size) * burst_size
```

---

# 4. DRAM Controller Design

## 4.1 Per-Bank Queue

각 bank마다 독립 큐를 유지한다:

```
BankQueue[bank].append(DRAMRequest)
```

## 4.2 Arbitration Policy

### 기본: FR-FCFS (First-Ready, First-Come, First-Serve)

우선순위:
1. Row-buffer hit 요청  
2. 오래 기다린 요청  

---

## 4.3 DRAM Tick Algorithm

```
for each channel:
    for each bank:
        if current_op in progress:
            continue

        req = select_request(bank)
        if req:
            if row_hit(req):
                delay = tBANK_HIT
            else:
                delay = tBANK_MISS

            schedule_burst(req, delay + tBURST)
```

---

# 5. NoC Model

## 5.1 NoC Topology

### 기본: 1-hop logical NoC (simplified)
- 모든 코어가 동일 DRAM controller에 연결된 전용 NoC  
- configurable topology:
  - fully-connected bus  
  - ring  
  - mesh (future)  

---

## 5.2 NoC Packet Structure

```
class NoCPacket:
    src_core
    dst_ctrl
    size_bytes
    hops
```

Latency:
```
latency = base + (hops * per_hop_delay)
```

Bandwidth:
```
per_cycle_capacity = link_bw_bytes
```

---

# 6. DMA Engine & Memory Subsystem Interaction

DMA 엔진은 실제 타일의 DRAM range를 기반으로 DRAM burst 요청을 생성한다.

## 6.1 DMA → NoC → DRAM controller flow

```
DMA generates burst
    →
NoC packetization
    →
DRAM controller (enqueue)
    →
service → NoC → DMA
```

---

# 7. Memory Stall Modeling

각 NPU core는 다음 원인으로 stall될 수 있다:

### 1. DMA waiting
- 이전 DMA copy가 끝나지 않음  
- DRAM queue congested  

### 2. NoC contention
- link capacity 초과  
- packet routing delay  

### 3. SPM allocation wait
- next tile에 필요한 SPM 공간 부족  
- previous tile이 SPM을 점유 중  

### 4. DRAM bank conflict
- multiple tiles mapping to same bank  

### 5. R/W switching penalty

---

# 8. DRAM/NoC-Aware Scheduling

Dynamic scheduler는 memory system 상태를 반영하여 tile 실행을 최적화한다.

### 8.1 Memory-aware heuristics
- T_tile이 짧은 load tile 먼저 수행  
- KV-load tile 우선순위 상승  
- 동일 bank로 향하는 연속 요청은 분산  

### 8.2 estimated stall prediction
```
stall_estimate(tile) =
    bank_conflict_prob * bank_penalty
  + size_bytes / effective_bw
```

---

# 9. KV-cache Specific Memory Modeling

KV-cache는 attention workload에서 DRAM의 80% 이상을 사용한다.

## 9.1 KV-Store (append)
- write-heavy burst  
- sequential DRAM addresses  
- row-buffer hit 비율 매우 높음  

## 9.2 KV-Load (range)
- read-heavy burst  
- 단일 head에 대해 연속적  
- multi-head에서 scatter 발생 → NoC contention 증가  
- row-buffer miss 가능성 증가  

## 9.3 Timeline impact
- KV-load stalls dominate decoder latency  
- tile-based breakdown 가능  

---

# 10. Timeline & Bandwidth Profiling

Profiler는 DRAM & NoC의 모든 이벤트를 기록한다.

## 10.1 DRAM Profile

- per-bank queue length  
- bank hit/miss ratio  
- row-buffer changes over time  
- read/write bandwidth  

## 10.2 NoC Profile

- packet injection time  
- link utilization graph  
- NoC stalls per tile  

## 10.3 Tile-level memory trace

각 타일에 대한 상세 이벤트 기록:

```
tile_id  
dram_req_start  
dram_req_end  
total_stall  
noc_hops  
bw_effective  
```

---

# 11. Validation Strategy

## 11.1 Microbenchmarks
- Single tile DMA  
- Multi-bank concurrent access  
- Variable burst size tests  

## 11.2 LLaMA Attention
- KV-load dominant pattern  
- Check memory stall timeline  
- Compare to analytic model  

## 11.3 Stress Test
- 8-core NPU  
- extreme KV lengths  
- DRAM saturation test  

---

# 12. Future Extensions

- HBM multi-channel modeling  
- Multi-chip NoC  
- Bank-group level policies  
- Adaptive prefetching model  
- Row-buffer locality predictor  

---

# End of Document
