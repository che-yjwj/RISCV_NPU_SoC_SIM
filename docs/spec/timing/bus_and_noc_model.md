# Bus & NoC Timing Specification
**Path:** `docs/spec/timing/bus_and_noc_model.md`  
**Version:** v1.1  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** System Performance Architect  
**Last Updated:** 2025-12-04

---

## 1. 목적
Host↔DRAM, DRAM↔NPU, NPU 내부 NoC의 대역폭/지연/중재 정책을 명시하여 DMA/TE/VE 레이턴시 모델이 동일한 버스 제약을 공유하도록 한다.

## 2. 계층 구조
1. **External DRAM Bus:** peak_bw_bytes_per_cycle, channel 수.
2. **On-chip NoC:** TE/VE/DMA/Trace 간 트래픽 전달, hop latency, arbitration 정책.
3. **Control Path:** CSR/MMIO 저지연 경로(참고용).

## 3. 파라미터
- `peak_bw_bytes_per_cycle`
- `num_channels`, channel interleaving function
- `noc_topology`: bus, mesh, crossbar 등
- `hop_latency_cycles`, `router_pipeline_depth`
- `arbitration_policy`: round-robin, priority-weighted
- `master_weights`: DMA / TE / Trace 등 마스터별 가중치
- `queue_depth_per_master`: 마스터별 outstanding 트랜잭션 상한
- `stall_event_threshold`: 큐가 꽉 찼을 때 stall 이벤트를 기록하는 임계치

## 4. Latency 모델
```
dram_cycles = bytes / effective_bw + t_setup
noc_cycles = hops * hop_latency_cycles + serialization_cost
bus_latency = max(dram_cycles, noc_cycles)
```
`effective_bw`는 동시 액티브 마스터 수로 나누어 계산하며, priority weight에 따라 분배 가능.

## 5. Contention
- **Shared bandwidth:** 동시에 `N`개의 DMA가 전송하면 `effective_bw = peak_bw / N`.
- **Priority override:** 긴급 트래픽(KV cache)에는 가중치 적용.
- **Backpressure 이벤트:** NoC 버퍼가 가득 차면 upstream DMA/TE 명령 issue 지연.

### 5.1 Queue-based Stall 모델
각 마스터(DMA channel/TE/VE)는 `queue_depth_per_master` 만큼 outstanding transaction을 보유할 수 있다.

```pseudo
if outstanding(master) >= queue_depth_per_master[master]:
    stall(master) = true
    emit_stall_event(master, reason="queue_full")
else:
    enqueue_request(master)
```

큐가 가득 차면 DMAEngine/DmaJob이 `stall` 상태로 유지되며,  
다음 사이클에 다시 enqueue를 시도한다. Trace에는 `stall_event`로 기록된다.

### 5.2 Priority-weighted Arbitration
`arbitration_policy="weighted_rr"` 설정 시, `master_weights`를 사용하여 토큰 기반 스케줄링을 수행한다.

```pseudo
token[master] += master_weights[master]
choose master with max token among ready masters
token[chosen] -= total_weight
```

KV 채널을 가진 DMA는 `master_weights["dma_kv"]=weight_high`로 설정해 Prefill/Decode 시 각 head가 장시간 대기하지 않도록 한다.

### 5.3 DRAM Stall/Resume 이벤트
- `stall_event` 발생 시: 어떤 master, 주소 범위, stall 시작 cycle을 Trace에 남긴다.
- `resume_event`: 해당 master가 다시 bus grant를 받았을 때 기록한다.
- `contention_counter`: master별 누적 stall cycle을 집계해 bottleneck 분석에 사용한다.

## 6. Trace Metrics
- `bandwidth_samples`: window별 read/write bytes (trace_format_spec 참고).
- `noc_queue_depth`: hop별 대기열 길이.
- `contention_events`: 언제 어떤 마스터가 stall 되었는지 기록.
- `stall_event`: queue_full, priority_preempt 등 상세 타입 포함.
- `master_utilization`: DMA/TE/VE 마스터별 bus 사용률(%)를 주기적으로 측정.

## 7. Validation
- channel address mapping이 DRAM 용량을 초과하지 않는지 체크.
- peak bandwidth 대비 평균 사용률을 계산해 비정상 사례(>100%) 탐지.
- master별 stall cycle과 weight 설정이 목표 QoS(예: KV DMA <= 5% stall)에 맞는지 확인.

## 8. 향후 확장
- HBM/Chiplet 연결 모델
- QoS 기반 arbitration
- Power-aware DVFS hook
