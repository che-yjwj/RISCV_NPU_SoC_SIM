# Tensor Engine Design
**Path:** `docs/design/te_engine_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
Tensor Engine(TE)은 GEMM/Conv 등 **행렬 기반 연산의 tile-level latency**를 모델링한다.  
이 문서는 TE의 job 모델, latency 계산, Trace와의 연계를 정의한다.

관련 스펙:
- `docs/spec/timing/te_timing_spec.md`
- `docs/spec/isa/cmdq_format_spec.md` (`TE_GEMM_TILE`)

## 2. 책임
- **입력**
  - `TE_GEMM_TILE` CMDQ 엔트리.
  - SPM 내 IFM/WGT/OFM 위치 정보 (bank/offset).
  - TE 성능 파라미터 (`macs_per_cycle_base`, bitwidth scaling 등).
- **출력**
  - TE job completion 이벤트.
  - TE 관련 `ENGINE_EVENT` trace (start_cycle, end_cycle, MAC 수 등).
- **주요 역할**
  - `m*n*k` MACs와 bitwidth를 TE 타이밍 수식에 넣어 tile latency 계산.
  - multi-TE 환경에서 각 TE의 busy 시간을 추적.
- **하지 말아야 할 일**
  - DMA/메모리 전송 수행.
  - tile 크기/스케줄링 변경.

## 3. 내부 구조

### 3.1 Job 구조
```python
class TeJob:
    cmdq_id: int
    te_id: int
    m: int
    n: int
    k: int
    qbits_weight: int
    qbits_activation: int
    start_cycle: Optional[int]
    end_cycle: Optional[int]
```

### 3.2 TE 상태
- `busy_until_cycle[te_id]`: 해당 TE가 free가 되는 cycle.
- `job_queue[te_id]`: 대기 중인 TeJob FIFO.

## 4. 알고리즘 / 플로우

### 4.1 Job 수락
- ControlFSM가 issue할 때:
  - target `te_id`가 busy가 아니면 즉시 job 시작.
  - busy이면 `job_queue[te_id]`에 enqueue.

### 4.2 Latency 계산
`te_timing_spec.md`에 따라:
```pseudo
MACs_tile = m * n * k
macs_per_cycle_eff = macs_per_cycle_base \
    * f_w(qbits_weight) * f_a(qbits_activation)
compute_cycles = ceil(MACs_tile / macs_per_cycle_eff)
latency = init_latency_cycles + compute_cycles + finalize_latency_cycles
```

### 4.3 per-cycle 업데이트
간단 모델에서는 TE가 “busy_until”로만 표현되므로, cycle마다 다음을 수행:
```pseudo
for each te_id:
    if busy_until_cycle[te_id] <= current_cycle and job_queue[te_id] not empty:
        job = job_queue[te_id].pop()
        job.start_cycle = current_cycle
        job.end_cycle = current_cycle + latency(job)
        busy_until_cycle[te_id] = job.end_cycle
        emit_engine_event_start(job)

    if just_reached(job.end_cycle):
        emit_completion_event(job.cmdq_id)
        emit_engine_event_end(job)
```

## 5. 인터페이스
- `TeEngine.submit(job: TeJob) -> None`
- `TeEngine.step(cycle: int, trace_engine) -> list[CompletionEvent]`
- `TeEngine.is_busy(te_id: int) -> bool`

구성 파라미터:
- `macs_per_cycle_base`
- `init_latency_cycles`, `finalize_latency_cycles`
- bitwidth scaling 함수 정의.

## 6. 예시 시나리오
- multi-TE 설정 (예: `num_te=2`)에서 GEMM 타일 여러 개가  
  TE0/TE1에 번갈아 배정되는지, trace에서 busy 구간이 병렬로 나타나는지 확인.

## 7. 향후 확장
- Conv 전용 타일 opcode 지원 (`TE_CONV_TILE`).
- sparsity-aware latency (sparsity ratio에 따른 MAC 감소).
- pipeline overlap 모델 (init/finalize latency amortization).
