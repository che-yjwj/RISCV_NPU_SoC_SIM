# Memory & NoC Model Specification (v1)

## 1. Purpose & Scope
본 문서는 RISC-V + xNPU ISA 기반 NPU 시뮬레이터에서 사용할 **메모리/NoC 모델(DRAM, SRAM, DMA, BW, Bank Conflict, Interconnect)**의 설계를 정의한다.

목표:
- DRAM 지연(latency) 및 대역폭(BW) 모델링 규칙 정의
- DMA 전송 단위, burst, 동시성(concurrency) 모델 정의
- On-chip SRAM(Scratchpad/Buffer)의 용량, bank, port 구조 및 bank conflict 규칙 정의
- NoC/Interconnect의 hop delay 및 공유 BW 모델 정의
- MicroScheduler/TE/VE/DMA와의 인터페이스 정의
- LLM/Transformer workload를 대상으로 하는 성능 분석에 적합한 수준의 추상화 제공

---

## 2. Memory Hierarchy Overview

### 2.1 계층 구조
```
[ RISC-V CPU ]
    │
    ├── L1/L2 Cache (optional, coarse 모델)
    │
    ├── Main Memory (DRAM Model)
    │
[ NPU Subsystem ]
    ├── DMAEngine
    │    └── NoC / Interconnect
    │          └── DRAM Controller(s)
    │
    ├── SRAM / Scratchpad
    │    ├── IFM Buffer
    │    ├── WGT Buffer
    │    ├── PSUM Buffer
    │    └── OFM Buffer / KV Cache
    │
    ├── TE (TensorEngine)
    └── VE (VectorEngine)
```

### 2.2 주요 목표
- DRAM BW/지연 제약이 TE/VE의 스루풋에 미치는 영향을 모델링
- SRAM bank conflict가 타일링 및 스케줄링에 미치는 영향 표현
- NoC 경합(contention)이 발생할 수 있는 단순 모델 제공

---

## 3. DRAM Model

### 3.1 Address Space
- 64-bit 물리 주소 공간 가정
- DRAM은 `MainMemory` 객체로 모델링
- NPU는 DMAEngine을 통해서만 DRAM에 접근

### 3.2 Latency Model
기본 latency 공식:
```text
access_latency = base_latency + (size_bytes / effective_bandwidth)
```
- `base_latency`: row activation, column access 등 고정 오버헤드
- `effective_bandwidth`: 채널 수, 데이터폭, 효율(overhead) 반영

### 3.3 Bandwidth & Channels
구성 파라미터:
- `dram_channel_count`
- `per_channel_peak_bw` (GB/s)
- `dram_efficiency` (0.0 ~ 1.0)

유효 BW:
```text
effective_bandwidth = dram_channel_count * per_channel_peak_bw * dram_efficiency
```

### 3.4 Contention Model
단순 모델 기준:
- 동일 사이클 구간에 여러 DMA transaction이 존재하면
- DRAM busy 윈도우가 겹치며, 대기열(queue)에서 순차 처리

대기 시간:
```text
wait_time = sum(previous_transactions_remaining_time)
```

---

## 4. NoC / Interconnect Model

### 4.1 Topology (초기 버전)
- 단순 shared bus 또는 single-hop crossbar로 모델링
- Optional: 2D mesh로 확장 (후속 버전)

### 4.2 Latency 요소
- `noc_fixed_latency`: hop 단위 고정 지연
- `noc_bw`: 링크 당 대역폭
- 전송 지연:
```text
noc_latency = noc_fixed_latency + (size_bytes / noc_bw)
```

### 4.3 Contention
- 한 cycle에 하나의 전송만 처리 가능한 큐 모델
- 또는 링크별 queueing model 적용
- DRAM busy 모델과 유사하게 NoC queue 지연 추가

---

## 5. SRAM / Scratchpad Model

### 5.1 Structure
- 용량: `sram_size_bytes`
- bank 수: `sram_bank_count`
- bank 당 port 수: `ports_per_bank` (R/W port 합)
- 영역 구분:
  - IFM buffer
  - WGT buffer
  - PSUM buffer
  - OFM/KV buffer

### 5.2 Addressing & Banking
SRAM 주소 → bank index 매핑:
```text
bank_id = (address / bank_stride) % sram_bank_count
```
- `bank_stride`는 data width 및 타일링 전략에 따라 설정
- 동일 cycle에 같은 bank에 대한 여러 access가 발생하면 conflict 발생

### 5.3 Bank Conflict Rule
- 은행당 동시 접근 허용 수 = `ports_per_bank`
- 한 cycle에 `ports_per_bank`를 초과하는 접근이 발생하면
  - 우선순위 규칙(예: TE>VE>DMA) 또는 라운드로빈으로 access 선택
  - 나머지는 다음 cycle로 미룸 (stall)

### 5.4 Latency
- SRAM 자체 접근 지연은 1~2 cycle로 가정
- bank conflict가 없으면 고정 지연
- conflict 시 TE/VE pipeline stage가 stall

---

## 6. DMA Model

### 6.1 DMA Channel
- 구성 파라미터:
  - `dma_channel_count`
  - 채널당 queue depth
- 각 채널은 DRAM ↔ SRAM 전송을 담당

### 6.2 Transaction 구조
```python
class DmaTransaction:
    tx_id: int
    src_addr: int
    dst_addr: int
    size_bytes: int
    direction: enum(DRAM_TO_SRAM, SRAM_TO_DRAM)
    state: enum(QUEUED, NOC_PENDING, DRAM_PENDING, COMPLETE)
    remaining_cycles: int
```

### 6.3 Cycle-Level 동작
1. MicroScheduler가 DmaTransaction 생성 후 DMAEngine queue에 push
2. DMAEngine은 각 cycle마다 다음을 수행:
   - 유휴 채널 찾기
   - Noc/DRAM에 요청 발행
   - `remaining_cycles` 감소
   - 0이 되면 COMPLETE로 전환, completion 이벤트 발생

---

## 7. Bank Conflict & Access Pattern

### 7.1 목적
- 타일링/배치에 따라 bank conflict 패턴이 어떻게 달라지는지 관찰 가능
- TE/VE 설계 및 타일링 전략을 변경하면서 성능 비교

### 7.2 Access 패턴 모델링
- TE: tile-based row-major access
- VE: vector-chunk access
- DMA: burst access

서로 다른 access 패턴이 동시에 발생할 때 bank conflict 개수를 카운트하고, stall cycle을 누적하여 TE/VE의 실제 유효 sustain BW를 시뮬레이션한다.

---

## 8. Integration with MicroScheduler / TE / VE

### 8.1 MicroScheduler 관점
- DMA job 발행 시
  - DRAM/NoC busy 여부 및 SRAM 여유 용량을 고려
- TE/VE job 발행 시
  - SRAM bank mapping을 고려하여 conflict 최소화 시도 (향후 bank-aware scheduler로 확장)

### 8.2 TE 관점
- tile 작업 시작 전, 해당 tile의 IFM/Weight가 SRAM에 존재해야 함
- SRAM access가 bank conflict로 지연되면 TE cycle이 stall 상태로 전환

### 8.3 VE 관점
- LN/Softmax/Rotary 연산 시 chunk 단위로 SRAM access
- bank conflict 발생 시 VE job latency 증가

---

## 9. Configuration Parameters

### 9.1 DRAM 관련
- `dram_channel_count`
- `dram_per_channel_bw` (GB/s)
- `dram_efficiency`
- `dram_base_latency`

### 9.2 NoC 관련
- `noc_topology` (BUS, CROSSBAR, MESH 등)
- `noc_fixed_latency`
- `noc_bw`

### 9.3 SRAM 관련
- `sram_size_bytes`
- `sram_bank_count`
- `sram_bank_stride`
- `sram_ports_per_bank`
- `sram_base_latency`

### 9.4 DMA 관련
- `dma_channel_count`
- `dma_queue_depth`
- `dma_burst_size`

이 파라미터들은 YAML/JSON으로 정의되고, 시뮬레이터 초기화 시 로딩된다.

---

## 10. Profiling & Metrics

### 10.1 측정 지표
- DRAM BW 사용률 (GB/s, % of peak)
- NoC BW 사용률
- DMA 대기 시간 (avg/max)
- SRAM bank conflict 비율
- TE/VE stall 비율

### 10.2 로그 이벤트 예시
- `DRAM_TX_START/END(tx_id, size, ch)`
- `NOC_TX_START/END(tx_id, size)`
- `SRAM_ACCESS(addr, bank_id, conflict)`
- `DMA_QUEUE_DEPTH(channel, depth)`

### 10.3 출력 형식
- JSON/CSV 기반 통계
- 타임라인/히스토그램/heatmap에 활용 가능

---

## 11. Future Extensions

1. 실제 DRAM timing model (row-hit/miss, bank group, refresh 등) 반영
2. Multi-controller DRAM 및 rank-level 병렬성 모델
3. Full NoC mesh/torus 토폴로지 + 라우팅 모델
4. QoS/priority-aware NoC scheduling
5. SRAM multi-banked multi-ported 구조의 상세 모델링
6. Energy/Power 모델과 연동 (access당 energy)

---

