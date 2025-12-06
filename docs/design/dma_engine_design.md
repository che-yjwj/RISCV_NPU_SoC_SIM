# DMA Engine Design
**Path:** `docs/design/dma_engine_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-04

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
  - burst, bandwidth, contention, SPM bank conflict, Bus/NoC stall을 고려한 latency 계산.
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
    head_id: Optional[int]         # KV 전용, multi-head 구분
    kv_kind: Optional[str]         # "k" / "v" (KV 전용)
    kv_range: Optional[KvRange]    # KV_LOAD 범위 (t_start/t_len/d_start/d_len)
    kv_layout_id: Optional[int]    # KV 레이아웃/stride 프로파일
    bytes_total: int
    bytes_aligned: int
    dram_addr: int
    spm_bank: int
    spm_offset: int
    remaining_bytes: int
    state: Literal["QUEUED", "TRANSFERRING", "COMPLETED"]
    stalled: bool                 # Bus/NoC queue가 full일 때 true
    stall_reason: Optional[str]
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

### 3.4 파이프라인 개략 다이어그램

```text
CMDQ(DMA_*_TILE)
      |
      v
 [DmaJob 생성] --> [QUEUE] --> [TRANSFERRING] --> [COMPLETED]
      |                              |
      |                        DRAM/Bus/NoC/SPM
      |                        bytes/latency 계산
      v
 TraceEngine (ENGINE_EVENT, MEM_ACCESS_EVENT)
```

- Timing 세부 공식은 `dma_timing_spec.md`를 따른다.  
- DMAEngine은 job 상태 전이와 bytes/latency 계산, Trace 기록을 담당한다.

### 3.5 KV 전용 필드/채널
- `KV_STORE_TILE`/`KV_LOAD_TILE`은 아래 매핑으로 DmaJob을 생성한다.  
  - STORE: `direction="write"`, `tensor_role="kv"`, `head_id`, `kv_kind`, `dram_addr=kv_base`, `t_start/t_len`, `qbits_kv`.  
  - LOAD: `direction="read"`, `tensor_role="kv"`, `head_id`, `kv_kind`, `kv_range`(t/d 범위), `qbits_kv`.  
- 채널 모델: activation/weight와 분리된 KV 채널(예: `kv_store`, `kv_load`)을 둘 수 있으며, `can_start_new_job()`에서 채널별 동시 전송 개수를 제한하거나 우선순위를 다르게 둘 수 있다.

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
        if memory_model.bus_can_enqueue(job):
            memory_model.enqueue(job)
            job.state = TRANSFERRING
            job.stalled = False
            job.stall_reason = None
            active_jobs.add(job)
        else:
            job.stalled = True
            job.stall_reason = "queue_full"
            emit_stall_event(job, cycle, reason=job.stall_reason)
            pending_queue.push_front(job)
            break  # Bus/NoC 큐가 가득 찼으므로 추가 enqueue 중단

    # 2) active job 진행
    for job in active_jobs:
        step_bytes = effective_bytes_per_cycle(active_jobs_count)
        if spm_or_bus_conflict(job):
            apply_conflict_penalty(job)
        else:
            job.remaining_bytes -= step_bytes
            emit_mem_access_events(job, step_bytes)

        if memory_model.backpressure(job):
            job.stalled = True
            job.stall_reason = "backpressure"
            emit_stall_event(job, cycle, reason=job.stall_reason)
            continue

        if job.remaining_bytes <= 0:
            job.state = COMPLETED
            emit_completion_event(job.cmdq_id)
            memory_model.dequeue(job)
            active_jobs.remove(job)
```

- `effective_bytes_per_cycle(active_jobs_count)`는 shared bandwidth 모델(`bus_and_noc_model.md`)을 따른다.
- `spm_or_bus_conflict(job)`는 `spm_model_spec.md`의 bank/port 규칙을 사용한다.
- `memory_model.bus_can_enqueue/backpressure/enqueue/dequeue`는 `bus_and_noc_model.md`에서 정의한 queue depth, priority, stall 정책을 따른다.

### 4.3 KV-aware 우선순위
- Prefill 단계: KV_STORE는 TE/VE가 생산한 결과를 누락 없이 DRAM에 적재해야 하므로, 동일 head에 대해 순서 보존 우선순위를 둔다(head + t_start 기반 정렬).  
- Decode 단계: KV_LOAD는 TE/VE 실행보다 앞서야 하므로, `pending_queue`에서 `tensor_role="kv"`에 소폭 가중치(+δ)를 부여해 먼저 시작한다.  
- 채널 분리 시: activation/weight DMA와 KV DMA를 교차 실행하되, `max_concurrent_transfers`를 channel별/total 두 계층으로 관리한다.

### 4.4 Trace 기록
- `MEM_ACCESS_EVENT`: DRAM/SPM 주소, 크기, 방향, source_engine=`DMA`.
- `ENGINE_EVENT`: job별 start_cycle/end_cycle 및 bytes.
- `bandwidth_samples`: window 단위로 read/write bytes 합산.
- `STALL_EVENT`: queue_full / priority_deferred / backpressure 등 stall 사유와 지속 시간을 기록.
- `RESUME_EVENT`: stalled job이 다시 grant를 받고 진행을 재개한 시점을 기록.

### 4.5 Bus/NoC 모델 연동
- DMAEngine은 `memory_model.tick()`으로부터 마스터별 grant 토큰/queue depth를 전달받는다.
- `master_weights`(`bus_and_noc_model.md`)에 따라 activation/weight DMA와 KV DMA가 각기 다른 grant 확률을 가진다.
- TraceEngine은 `noc_queue_depth`, `stall_event` 메트릭을 기록하여 DRAM/NoC 병목 분석에 활용한다.

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
- Prefill/Decode 분리:
  - Prefill: TE/VE 출력 → KV_STORE_TILE이 순서대로 기록되고, head/t_start 순서가 보존되는지 확인.
  - Decode: step마다 KV_LOAD_TILE이 TE/VE보다 먼저 issue되어 fetch latency가 숨겨지는지, channel별 동시성/우선순위 설정이 의도대로 동작하는지 확인.

## 7. 향후 확장
- 2D/ND DMA stride 지원.
- 압축/해제 DMA (compressed tensor 전송).
- multi-channel DRAM, 채널 interleaving 모델.
