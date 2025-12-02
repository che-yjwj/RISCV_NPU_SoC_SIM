# DMA Engine Design
**Path:** `docs/design/dma_engine_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
DMAEngine은 DRAM↔SPM 데이터 전송에 대한 **latency/bandwidth 모델을 구현**하는 시뮬레이터 엔진이다.  
이 문서는 DMAEngine의 데이터 구조, 타이밍 계산, MemoryModel/TraceEngine과의 상호작용을 정의한다.

관련 스펙:
- `docs/spec/timing/dma_timing_spec.md`
- `docs/spec/quantization/bitwidth_memory_mapping.md`
- `docs/spec/timing/spm_model_spec.md`
- `docs/spec/timing/bus_and_noc_model.md`

## 2. 책임
- **입력**
  - CMDQ의 `DMA_LOAD_TILE` / `DMA_STORE_TILE` 엔트리.
  - DRAM/Bus/SPM 설정 (bandwidth, alignment, bank 수 등).
- **출력**
  - DMA job completion 이벤트 (`cmdq_id`, 완료 cycle).
  - DRAM/Bus/SPM access trace (`ENGINE_EVENT`, `MEM_ACCESS_EVENT`, `bandwidth_samples`).
- **주요 역할**
  - `num_elements`, `qbits`로부터 bytes/bytes_aligned 계산.
  - burst, bandwidth, contention, SPM bank conflict를 고려한 latency 계산.
- **하지 말아야 할 일**
  - TE/VE 연산 수행.
  - 타일링/스케줄링 결정 변경 (CMDQ는 이미 결정된 결과).

## 3. 내부 구조

### 3.1 Job 구조
```python
class DmaJob:
    cmdq_id: int
    direction: Literal["read", "write"]
    tensor_role: str
    bytes_total: int
    bytes_aligned: int
    dram_addr: int
    spm_bank: int
    spm_offset: int
    remaining_bytes: int
    state: Literal["QUEUED", "TRANSFERRING", "COMPLETED"]
```

### 3.2 큐 및 상태
- `pending_queue`: 아직 시작하지 않은 DmaJob FIFO.
- `active_jobs`: 현재 진행 중인 전송 목록 (shared bandwidth 모델에서 다수 허용).
- `stats`: 누적 DRAM bytes, job 수, 평균 latency 등.

### 3.3 상태 전이 개략

```text
           +-----------+
           |  QUEUED   |
           +-----------+
                 |
                 | can_start_new_job()
                 v
           +--------------+
           | TRANSFERRING |
           +--------------+
                 |
                 | remaining_bytes <= 0
                 v
           +-----------+
           | COMPLETED |
           +-----------+
```

- QUEUED → TRANSFERRING: Bus/NoC/SPM 여건이 허용되는 순간 시작.
- TRANSFERRING → COMPLETED: 모든 bytes 전송 후 completion 이벤트 및 trace 기록.

## 4. 알고리즘 / 플로우

### 4.1 Job 생성
CMDQ 엔트리 → DmaJob 매핑:
1. `num_elements`, `qbits`로 `bytes_total` 계산.
2. alignment 규칙으로 `bytes_aligned` 계산.
3. `direction`은 opcode 종류로부터 결정(LOAD=read, STORE=write).
4. `pending_queue`에 enqueue.

### 4.2 per-cycle 업데이트
`dma_timing_spec.md`의 모델을 따른다.

```pseudo
for each cycle:
    # 1) 새로운 job 시작 조건 확인
    while pending_queue not empty and can_start_new_job():
        job = pending_queue.pop()
        job.state = TRANSFERRING
        active_jobs.add(job)

    # 2) active job 진행
    for job in active_jobs:
        step_bytes = effective_bytes_per_cycle(active_jobs_count)
        if spm_or_bus_conflict(job):
            apply_conflict_penalty(job)
        else:
            job.remaining_bytes -= step_bytes
            emit_mem_access_events(job, step_bytes)

        if job.remaining_bytes <= 0:
            job.state = COMPLETED
            emit_completion_event(job.cmdq_id)
            active_jobs.remove(job)
```

- `effective_bytes_per_cycle(active_jobs_count)`는 shared bandwidth 모델(`bus_and_noc_model.md`)을 따른다.
- `spm_or_bus_conflict(job)`는 `spm_model_spec.md`의 bank/port 규칙을 사용한다.

### 4.3 Trace 기록
- `MEM_ACCESS_EVENT`: DRAM/SPM 주소, 크기, 방향, source_engine=`DMA`.
- `ENGINE_EVENT`: job별 start_cycle/end_cycle 및 bytes.
- `bandwidth_samples`: window 단위로 read/write bytes 합산.

## 5. 인터페이스
- `DmaEngine.submit(job: DmaJob) -> None`
- `DmaEngine.step(cycle: int, memory_model, trace_engine) -> list[CompletionEvent]`
- `DmaEngine.flush() -> None` (남은 job 없는지 검증).

구성 파라미터:
- `max_concurrent_transfers`
- `peak_bw_bytes_per_cycle`
- alignment 정책, burst 길이 등.

## 6. 예시 시나리오
- CMDQ에 KV cache LOAD/STORE가 섞여 있는 LLM workload:
  - low-bit KV(4bit)와 activation(8bit)의 bytes 차이가 latency에 반영되는지  
    Trace를 통해 확인.

## 7. 향후 확장
- 2D/ND DMA stride 지원.
- 압축/해제 DMA (compressed tensor 전송).
- multi-channel DRAM, 채널 interleaving 모델.
