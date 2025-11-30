<!-- status: draft -->
# TDD – Py-V Integration with xNPU ISA (v1)

## 1. Purpose
본 문서는 Py-V RISC-V 시뮬레이터와 xNPU ISA 기반 NPU 서브시스템을 통합하기 위한 **Technical Design Document(TDD)**이다. 목표는 CPU–NPU 전체 경로를 cycle-level 또는 near-cycle 수준으로 구현할 수 있는 아키텍처 명세를 제공하는 것이다.

본 TDD는 다음 기능을 다룬다:
- RISC-V CPU의 xNPU ISA decode/execute 경로 설계
- MMIO 기반 NPU 접근 경로 설계
- CPU–Bus–NPU의 일관된 데이터 흐름 정의
- CommandQueue, MicroScheduler, DMA, TE, VE, Interrupt의 작동 구조 정의
- Cycle simulation 엔진 설계
- 프로파일링 및 이벤트 로깅 구조

---

## 2. System Architecture
```
PyVSimulator
 ├── CpuCore
 │     ├── Frontend (IF/ID)
 │     ├── Execute
 │     ├── LSU (MMIO/Memory)
 │     └── CSR File
 ├── Bus
 │     ├── MainMemory
 │     └── NpuMmioDevice
 ├── NpuDevice
 │     ├── CommandQueue
 │     ├── MicroScheduler
 │     ├── DMAEngine
 │     ├── TensorEngine (TE)
 │     ├── VectorEngine (VE)
 │     └── SRAM / BufferManager
 └── InterruptController
```
CPU Frontend는 xNPU ISA를 decode하며, LSU는 NPU MMIO 영역을 감지하여 처리한다. NpuDevice는 ISA 및 MMIO 두 frontend로부터 job을 enqueue하여 MicroScheduler로 전달한다.

---

## 3. CPU–NPU Interfaces

### 3.1 xNPU ISA Path
```
XNPU.LAUNCH   → CSR write → NPU doorbell → enqueue
XNPU.MATMUL   → descriptor 주소를 사용하여 enqueue
XNPU.LAYERNORM / SOFTMAX_1D / VOP 등 → VE 실행 job enqueue
```
CPU는 ISA 디코드 후 즉시 NPUDevice.enqueue()를 호출한다.

### 3.2 MMIO Path
LSU는 store 명령을 Bus로 전달
→ Bus가 주소를 NpuMmioDevice 범위와 비교
→ 해당 레지스터에 write
→ START bit write 시 doorbell 발생 → enqueue()

두 방식 모두 내부적으로 동일한 enqueue pipeline을 사용한다.

---

## 4. CommandQueue
```
class CommandEntry:
    cmd_id: int
    desc_addr: int
    cmd_type: enum(XNPU_OP)
    source: "ISA" or "MMIO"
    token: int
    state: enum(IDLE, READY, DISPATCH, ACTIVE, COMPLETE)
```
Queue는 FIFO 또는 priority 기반으로 구성할 수 있다.
MicroScheduler는 READY 상태의 항목을 선택하여 실행 준비를 한다.

---

## 5. MicroScheduler
MicroScheduler는 NPU 내부의 제어 중심부이다.

### 5.1 Event Loop
```
while True:
    fetch_command()
    parse_descriptor()
    plan_dma()
    schedule_te_ve()
    wait_te_ve_finish()
    writeback()
    generate_interrupt()
```

### 5.2 Descriptor Handling
Descriptor는 RAM에 저장되며 다음 정보를 포함한다:
- src/dst 주소
- shape/stride
- datatype
- flags(fusion, mask, rotary 등)

MicroScheduler는 descriptor를 해석하여 TE/VE 실행 파라미터를 생성한다.

### 5.3 TE/VE Scheduling
- TE job과 VE job은 병렬 실행 가능
- DMA–Compute Overlap 규칙 적용
- 앞선 job의 token dependency 만족 시 다음 job 실행

---

## 6. DMA Engine
### 6.1 기능
- DRAM ↔ SRAM 간 이동
- burst 기반 latency/BW 모델링
- alignment rule 적용

### 6.2 Cycle Model
```
if bus_free:
    start_burst()
else:
    wait
```
TE/VE 실행에 필요한 IFM/Weights/PSUM/OFM을 호출 순서에 맞춰 프리페치한다.

---

## 7. Tensor Engine (TE)

### 7.1 기능
- GEMM/MATMUL 실행
- tile 기반 MAC 연산
- pipeline depth 및 MAC latency 반영

### 7.2 Cycle Model
```
for tile in tiles:
    dma_wait(tile.ifm, tile.weight)
    compute(tile)
    psum_merge(tile)
```

---

## 8. Vector Engine (VE)

### 8.1 기능
- LayerNorm, RMSNorm
- Softmax 1D
- Rotary 1D
- Activation/GELU/SILU
- Residual/bias/add

### 8.2 Cycle Model
```
for chunk in chunks:
    dma_wait(chunk.src)
    execute_vector_kernel(chunk)
    dma_store(chunk.dst)
```

---

## 9. SRAM / Buffer Manager
- Bank/Port 구조 모델링
- Conflict rule 적용
- Allocation/free 정책
- TE/VE 메모리 동시성 검증

---

## 10. NPU Tick Model
```
def npu_tick():
    dma_engine.step()
    te.step()
    ve.step()
    micro_scheduler.step()
```
전체 시스템은 CPU Tick + NPU Tick으로 구성된다.

---

## 11. Interrupt Path
- TE/VE job 종료 시 NPUDevice가 interrupt signal set
- InterruptController가 CPU 외부 인터럽트 라인 활성화
- CPU는 trap handler에서 xnpu_status CSR 읽기
- token 기반 완료 처리

---

## 12. Profiling & Logging
### 12.1 Event Types
- DMA_START, DMA_END
- TE_START, TE_END
- VE_START, VE_END
- CMD_DISPATCH, CMD_COMPLETE
- IRQ_EMIT

### 12.2 Export
- JSON event dump
- Gantt chart generator
- DMA BW plot
- TE/VE utilization plot

---

## 13. Test Plan
### 13.1 Unit Tests
- ISA instruction decode
- MMIO register access
- descriptor parsing
- DMA path correctness
- TE/VE kernel correctness

### 13.2 Integration Tests
- LN→GEMM→ACT pipeline
- Softmax→V MatMul pipeline
- KV Cache update path

### 13.3 Stress Tests
- multi-tenancy (multi-context switching)
- long sequence(QKV/Softmax/V) LLM block 실행
- DRAM BW 제한 환경

---

## 14. 확장 계획
1. Attention Block ISA 추가
2. Graph Launch ISA
3. auto-tuning 기반 kernel selector
4. bank-aware scheduler
5. detailed NoC/mesh model

---

