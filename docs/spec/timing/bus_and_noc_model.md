# Bus & NoC Timing Specification
**Path:** `docs/spec/timing/bus_and_noc_model.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** System Performance Architect  
**Last Updated:** YYYY-MM-DD

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

## 6. Trace Metrics
- `bandwidth_samples`: window별 read/write bytes (trace_format_spec 참고).
- `noc_queue_depth`: hop별 대기열 길이.
- `contention_events`: 언제 어떤 마스터가 stall 되었는지 기록.

## 7. Validation
- channel address mapping이 DRAM 용량을 초과하지 않는지 체크.
- peak bandwidth 대비 평균 사용률을 계산해 비정상 사례(>100%) 탐지.

## 8. 향후 확장
- HBM/Chiplet 연결 모델
- QoS 기반 arbitration
- Power-aware DVFS hook
