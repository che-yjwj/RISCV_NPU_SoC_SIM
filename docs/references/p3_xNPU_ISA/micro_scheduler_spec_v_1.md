# MicroScheduler Specification (v1)

## 1. Purpose & Scope
MicroScheduler는 xNPU ISA 및 MMIO front-end로부터 전달된 NPU 명령을 해석하고, DMA/TE/VE/SRAM을 제어하여 실제 연산을 수행하는 **NPU 제어 핵심 모듈**이다.

이 Spec의 목적은 다음을 정의하는 것이다.
- MicroScheduler의 **기능적 역할**
- 입력/출력 인터페이스와 상태 머신
- CommandQueue, Job, Token, Dependency 구조
- DMA/TE/VE 스케줄링 알고리즘
- 멀티테넌시/토큰 기반 동기화 방식
- Py-V 기반 시뮬레이터에서의 cycle-level 동작 모델

---

## 2. High-Level Role
MicroScheduler는 다음을 수행한다.
1. CommandQueue에서 실행 가능한 명령(CommandEntry)을 선택
2. Descriptor를 DRAM에서 fetch하여 연산 파라미터를 추출
3. DMAEngine을 통해 IFM/Weights/OFM/KV cache 등을 SRAM으로 이동
4. TensorEngine(TE) 및 VectorEngine(VE)에 job을 발행
5. TE/VE 실행 완료 이벤트를 수집하고, 후속 job/command를 활성화
6. Command 단위 완료 시 Token/Status를 갱신하고 Interrupt를 발생

MicroScheduler는 TE/VE 선택, 타일링, DMA-Compute overlap, SRAM bank 사용 등을 통합적으로 관리하는 **중앙 스케줄러**이다.

---

## 3. Interfaces

### 3.1 Inputs
- CommandQueue에서의 CommandEntry
- Descriptor 메모리(ONNX/IR 기반 descriptor stream)
- xNPU ISA/driver로부터 전달된 config (SRAM size, DMA channel 수 등)
- DMA/TE/VE에서 올라오는 completion 이벤트

### 3.2 Outputs
- DMAEngine에 대한 DMA 요청 (read/write)
- TE에 대한 tile-level GEMM/MATMUL job
- VE에 대한 vector-level job (LN/Softmax/Rotary/Act 등)
- NpuStatus (busy/idle/error, current command ID)
- InterruptController에 대한 IRQ 트리거

---

## 4. Data Structures

### 4.1 CommandEntry
```python
class CommandEntry:
    cmd_id: int            # unique id
    desc_addr: int         # descriptor pointer (DRAM address)
    cmd_type: XnpuOpType   # MATMUL, LAYERNORM, SOFTMAX_1D, etc.
    source: str            # "ISA" or "MMIO"
    token: int             # completion token exposed to CPU
    priority: int          # optional
    state: CmdState        # IDLE, READY, DISPATCH, ACTIVE, COMPLETE
```

### 4.2 Job Descriptor (Internal)
TE/VE 실행 단위로 사용하는 내부 Job 구조:
```python
class Job:
    job_id: int
    cmd_id: int
    job_type: JobType      # TE_GEMM, VE_LN, VE_SOFTMAX, DMA_ONLY, etc.
    tile_info: TileInfo    # TE용 (M,N,K, tile index 등)
    vec_info: VecInfo      # VE용 (len, stride, batch 등)
    deps: list[int]        # 선행 job_id 목록
    users: list[int]       # 후속 job_id 목록
    ready: bool
    issued: bool
    done: bool
```

### 4.3 Dependency Graph
- 각 Command는 여러 Job으로 분해됨
- Job들은 directed acyclic graph(DAG)로 표현
- MicroScheduler는 **ready && resource-available**인 Job을 선택하여 issue

### 4.4 Token Table
```python
class TokenEntry:
    token: int
    cmd_id: int
    completed: bool
    done_cycle: int
```
- xNPU ISA의 `WAIT` 명령 또는 드라이버가 completion 여부를 확인할 때 사용

---

## 5. State Machine

### 5.1 Command State
- **IDLE**: queue에 존재하나 descriptor fetch 전
- **READY**: descriptor fetch 완료, job graph 생성 완료
- **DISPATCH**: 하나 이상의 job이 실행 중
- **ACTIVE**: 모든 job이 생성되었고 일부가 실행/대기 상태
- **COMPLETE**: 모든 job done, token 완료, IRQ 발생

### 5.2 Job State
- `ready = (all deps.done == True)`
- `issued = True` 후 TE/VE/DMA에 전달
- TE/VE/DMA completion 시 `done = True`

---

## 6. Scheduling Algorithm

### 6.1 Top-Level Event Loop
의사코드:
```python
def step(cycle):
    # 1) 새 command 준비
    _update_ready_commands()

    # 2) 각 ready command에 대해 job 그래프 업데이트
    for cmd in ready_commands:
        _build_jobs_if_needed(cmd)

    # 3) job 레벨 스케줄링
    _schedule_jobs(cycle)

    # 4) completion / token / interrupt 처리
    _update_completion(cycle)
```

### 6.2 Job Scheduling
```python
def _schedule_jobs(cycle):
    ready_jobs = [j for j in job_pool if j.ready and not j.issued]

    # 우선순위: (cmd.priority, job_type, age 등)
    ready_jobs.sort(key=scheduling_key)

    for job in ready_jobs:
        if _resource_available(job):
            _issue_job(job, cycle)
```

### 6.3 Resource Availability Check
- DMA 채널 사용 여부
- TE/VE busy 여부
- SRAM bank conflict 여부
- 드라이버/Config에서 정의한 동시 실행 제한

```python
def _resource_available(job):
    if job.job_type in TE_TYPES and te.is_busy():
        return False
    if job.job_type in VE_TYPES and ve.is_busy():
        return False
    if _sram_conflict(job):
        return False
    if job.job_type in DMA_TYPES and not dma.has_free_channel():
        return False
    return True
```

---

## 7. DMA–Compute Overlap

### 7.1 목표
- TE/VE의 compute 시간 뒤에 DMA latency를 최대한 숨김
- 다음 tile/segment의 데이터를 미리 fetch

### 7.2 정책
1. **Prefetch Jobs**: DMA-only job을 TE/VE job보다 우선하거나 적어도 동등하게 스케줄링
2. **Lookahead**: 현재 실행 중인 TE/VE job의 후속 tile들의 DMA를 미리 발행
3. **Backpressure**: SRAM capacity 및 bank conflict가 있을 경우 DMA 발행 제한

의사코드:
```python
def _plan_dma_for_te_job(te_job):
    for next_tile in te_job.future_tiles:
        if not _dma_planned(next_tile) and _sram_space_ok(next_tile):
            create_dma_job_for(next_tile)
```

---

## 8. TE/VE Co-Scheduling

### 8.1 목표
- TE job과 VE job이 동시에 실행되도록 해 전체 NPU utilization을 높임
- 예: LN(VE)와 다음 layer의 GEMM(TE)를 overlap

### 8.2 정책
- TE와 VE는 서로 다른 resource pool
- Job scheduling 시 TE/VE job을 동시에 발행 가능

```python
def _schedule_jobs(cycle):
    # TE, VE, DMA 각각에 대해 사용 가능한 job 선택
    for job in ready_jobs:
        if job.job_type in TE_TYPES and te.free():
            _issue_job(job, cycle)
        elif job.job_type in VE_TYPES and ve.free():
            _issue_job(job, cycle)
        elif job.job_type in DMA_TYPES and dma.has_free_channel():
            _issue_job(job, cycle)
```

---

## 9. Multitenancy & Context

### 9.1 Command Isolation
- 각 CommandEntry는 `cmd_id` 및 `token`으로 식별
- MicroScheduler는 서로 다른 프로세스/모델의 command를 동일 queue에서 처리 가능

### 9.2 Context Save/Restore (시뮬레이터 관점)
- 실제 HW에서는 복잡하지만, 시뮬레이터에서는 다음을 상태로 유지
  - CommandQueue state
  - job_pool 및 각 job 상태
  - DMA/TE/VE FIFO 상태
  - SRAM occupancy

- Preemption 시 위 상태를 스냅샷으로 저장/복원 가능하게 설계

---

## 10. Error Handling

- Descriptor invalid (out-of-range addr, align 위반 등)
- DMA timeout
- TE/VE internal error

에러 발생 시:
1. 해당 command를 실패 상태로 마킹
2. token completed = True + error flag
3. NpuStatus.error = True 설정
4. IRQ 발생, CPU/드라이버가 에러 처리

---

## 11. Cycle-Level Simulation Model

### 11.1 Tick 순서
Py-V 시뮬레이터에서 한 cycle은 다음 순서로 진행된다.

```python
def sim_tick(cycle):
    cpu.tick()              # RISC-V pipeline advance
    npu.dma_engine.step()
    npu.te.step()
    npu.ve.step()
    npu.micro_scheduler.step(cycle)
    irq_ctrl.step()
```

### 11.2 Latency 모델링
- DMA: base_latency + size / bandwidth
- TE: pipeline_depth + tile_cycles
- VE: vector_length / lanes + overhead

각 step에서 내부 counter를 감소시키고 0이 되면 completion 이벤트 발생.

---

## 12. Profiling Hooks

### 12.1 Event Types
- `CMD_ENQUEUE(cmd_id)`
- `CMD_START(cmd_id)` / `CMD_END(cmd_id)`
- `JOB_ISSUE(job_id, cmd_id, job_type)`
- `JOB_DONE(job_id, cmd_id)`
- `DMA_START/END`
- `TE_START/END`
- `VE_START/END`
- `IRQ_EMIT(cmd_id, token)`

### 12.2 Export Format
- JSON lines 혹은 trace array로 export
- Gantt chart/Timeline/Utilization 계산에 사용

---

## 13. Configuration Parameters

- `max_inflight_commands`
- `max_jobs_per_command`
- `dma_channel_count`
- `te_peak_tflops`
- `ve_vector_width`
- `sram_size`
- `sram_bank_count`
- `enable_multitenancy`
- `enable_prefetch`

이 매개변수들은 MicroScheduler 초기화 시 주입되며, 다양한 NPU 아키텍처를 시뮬레이션하는 데 사용된다.

---

## 14. Roadmap for MicroScheduler Enhancements

1. Bank-aware scheduler (SRAM bank conflict 최소화)
2. NoC/mesh topology-aware DMA scheduling
3. Power-aware scheduling (activity 기반 전력 추정)
4. LLM-specific 패턴 인식(Attention block 최적화)
5. MLP/Attention block-level job graph 자동 생성기

---

