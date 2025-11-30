<!-- status: draft -->
시뮬레이션 시간 축 구현을 “전역 sim_cycle 기반 tick() 모델”로 구체화한 것이 본 문서의 역할이다.


---

## 📄 `docs/design/design_sim_engine_cycle_kernel.md`

```markdown
# Design – Global Cycle-Based Simulation Kernel (CPU Cycle Loop)

## 1. 목적

본 문서는 RISC-V + xNPU ISA 기반 시뮬레이터에서  
**전역 CPU cycle loop 하나로 통일된 cycle-based 시뮬레이션 커널**의 구체적인 설계를 정의한다.

- 어떤 클래스들이 어떤 책임을 가지는지
- tick 순서와 인터페이스
- 서로 다른 “클럭 속도”를 가진 모듈을 어떻게 sim_cycle로 통합하는지
- MicroScheduler, DMA, TE/VE, Memory/NoC/Profiler가 이 커널 위에서 어떻게 동작하는지

를 명시한다.

---

## 2. Top-Level 구조

### 2.1 클래스 구조 개요

```text
Simulator
 ├── CpuCore          (RISC-V Py-V)
 ├── NpuSystem
 │     ├── MicroScheduler
 │     ├── DmaEngine
 │     ├── TensorEngine (TE)
 │     ├── VectorEngine (VE)
 │     └── SramSystem
 ├── MemorySystem
 │     └── DramModel
 ├── NoC
 ├── InterruptController
 └── Profiler


각 모듈은 공통적으로 tick(sim_cycle: int) 메서드를 가진다.

3. Simulator 메인 루프
class Simulator:
    def __init__(self, config):
        self.sim_cycle = 0
        self.cpu = CpuCore(config.cpu)
        self.npu = NpuSystem(config.npu)
        self.mem = MemorySystem(config.mem)
        self.noc = NoC(config.noc)
        self.irq = InterruptController(config.irq)
        self.profiler = Profiler(config.profiler)

    def run(self, max_cycles: int):
        for cycle in range(max_cycles):
            self.sim_cycle = cycle

            # 1) CPU tick
            self.cpu.tick(cycle)

            # 2) NPU tick
            self.npu.tick(cycle)

            # 3) Memory / NoC tick
            self.mem.tick(cycle)
            self.noc.tick(cycle)

            # 4) Interrupt handling
            self.irq.tick(cycle, cpu=self.cpu, npu=self.npu)

            # 5) Profiling / Trace
            self.profiler.tick(cycle, self)

            if self._done():
                break

tick 호출 순서 원칙

CPU → 2. NPU → 3. Memory/NoC → 4. IRQ → 5. Profiler
순서는 필요에 따라 조정 가능하나, 일관성 있게 유지해야 한다.

4. Multi-Clock 추상화: period / local_phase
4.1 공통 베이스 클래스
class Tickable:
    def __init__(self, period: int = 1):
        self.period = max(1, period)  # 최소 1
        self._phase = 0               # local_phase

    def tick(self, sim_cycle: int):
        self._phase += 1
        if self._phase < self.period:
            return  # 이 sim_cycle에는 실제 local cycle 없음
        self._phase = 0
        self._tick_local(sim_cycle)

    def _tick_local(self, sim_cycle: int):
        raise NotImplementedError


모든 컴포넌트(CpuCore, NpuSystem, DramModel, NoC 등)는 Tickable을 상속한다.

period를 이용해 각자의 속도를 조절:

period=1 → 매 sim_cycle마다 local cycle 1회

period=2 → 2 sim_cycle마다 local cycle 1회

period=4 → 4 sim_cycle마다 local cycle 1회

4.2 예시: CPU / NPU / DRAM 설정
class CpuCore(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.cpu_period)
        ...

    def _tick_local(self, sim_cycle):
        self._advance_one_cpu_cycle()

class NpuSystem(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.npu_period)
        ...

    def _tick_local(self, sim_cycle):
        self._advance_one_npu_cycle()

class DramModel(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.dram_period)
        ...

    def _tick_local(self, sim_cycle):
        self._advance_one_dram_cycle()


cfg.cpu_period, cfg.npu_period, cfg.dram_period는
config 파일(JSON/YAML)에서 로딩한다.

5. NpuSystem 내부 tick 설계
class NpuSystem(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.npu_period)
        self.scheduler = MicroScheduler(cfg.scheduler)
        self.dma = DmaEngine(cfg.dma)
        self.te = TensorEngine(cfg.te)
        self.ve = VectorEngine(cfg.ve)
        self.sram = SramSystem(cfg.sram)

    def _tick_local(self, sim_cycle: int):
        # 순서는 설계에 따라 조정 가능
        self.scheduler.tick(sim_cycle, self)
        self.dma.tick(sim_cycle, self)
        self.te.tick(sim_cycle, self)
        self.ve.tick(sim_cycle, self)
        self.sram.tick(sim_cycle, self)

5.1 MicroScheduler tick

MicroScheduler는 cycle-based 모드에서 다음을 수행한다.

class MicroScheduler(Tickable):
    def __init__(self, cfg):
        super().__init__(period=1)  # NPU local cycle마다 동작
        ...

    def _tick_local(self, sim_cycle: int, npu: "NpuSystem"):
        # 1) 새 command 상태 업데이트
        self._update_commands(sim_cycle)

        # 2) ready job 탐색
        ready_jobs = self._find_ready_jobs()

        # 3) resource(TE/VE/DMA/SRAM) 상태 확인
        for job in ready_jobs:
            if self._can_issue(job, npu):
                self._issue_job(job, npu, sim_cycle)


DMA/TE/VE가 job 완료 시 scheduler의 내부 플래그를 업데이트하여
다음 tick에서 ready_jobs로 올라오도록 한다.

별도의 이벤트 커널 없이도 cycle-based로 Job graph를 평가한다.

6. DMAEngine tick 설계
class DmaEngine(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.npu_period)  # NPU와 동일 클럭 도메인 가정
        self.channels = [...]
        # 각 채널: inflight transaction 목록

    def _tick_local(self, sim_cycle: int, npu: "NpuSystem" = None):
        for ch in self.channels:
            self._tick_channel(ch, sim_cycle)

    def _tick_channel(self, ch, sim_cycle: int):
        if ch.current_tx is None and ch.queue:
            ch.current_tx = ch.queue.pop(0)
            ch.current_tx.remaining_cycles = self._compute_latency(ch.current_tx)

        if ch.current_tx:
            ch.current_tx.remaining_cycles -= 1
            if ch.current_tx.remaining_cycles <= 0:
                self._complete_tx(ch.current_tx, sim_cycle)
                ch.current_tx = None


_compute_latency()는 Memory/NoC Spec에서 정의한
size / BW + base_latency를 sim_cycle 기준으로 환산한 값.

remaining_cycles는 sim_cycle 기준이며,
DRAM/NoC의 상대적 속도는 latency 계산에 포함된다.

7. TensorEngine / VectorEngine tick 설계
class TensorEngine(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.npu_period)
        self.current_job = None

    def launch_job(self, job, sim_cycle: int):
        # Scheduler가 호출
        self.current_job = job
        job.remaining_cycles = self._compute_job_latency(job)

    def _tick_local(self, sim_cycle: int, npu: "NpuSystem" = None):
        if self.current_job is None:
            return
        self.current_job.remaining_cycles -= 1
        if self.current_job.remaining_cycles <= 0:
            self._complete_job(self.current_job, sim_cycle)
            self.current_job = None


VE도 동일 패턴:

class VectorEngine(Tickable):
    ...


latency 계산 시, SRAM bank conflict penalty, DRAM access stall 등을 포함하거나,
또는 해당 penalty는 SRAM/Memory 모델에서 계산한 값을 반영할 수 있다.

8. Memory/NoC tick 설계
class MemorySystem(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.dram_period)
        self.dram = DramModel(cfg.dram)

    def _tick_local(self, sim_cycle: int):
        self.dram._tick_local(sim_cycle)


NoC도 마찬가지로 Tickable 기반:

class NoC(Tickable):
    def __init__(self, cfg):
        super().__init__(period=cfg.noc_period)
        self.links = [...]

    def _tick_local(self, sim_cycle: int):
        for link in self.links:
            link.transfer_step()

9. Profiler & Trace 연동

Profiler는 전역 sim_cycle을 기준으로 이벤트를 수집한다.

class Profiler(Tickable):
    def __init__(self, cfg):
        super().__init__(period=1)  # 매 sim_cycle마다 관찰 가능
        self.trace_writer = ...

    def _tick_local(self, sim_cycle: int, sim: "Simulator"):
        # 예시: TE/VE/DMA/DRAM busy 상태를 관찰
        self._log_component_states(sim_cycle, sim)

    def _log_component_states(self, sim_cycle, sim):
        # 필요 시 event 기반 trace로 변환
        if sim.npu.te.current_job is not None:
            self.trace_writer.log({
                "event_type": "TE_BUSY",
                "t_cycle": sim_cycle,
                "cmd_id": sim.npu.te.current_job.cmd_id,
            })


더 정교한 이벤트(TE_START/END, DMA_START/END 등)는
각 모듈의 상태 변화 시점에 직접 trace를 기록한다.

핵심은 기준 시간이 항상 sim_cycle이라는 것이다.

10. Config 예시
sim:
  max_cycles: 1000000

clock:
  cpu_period: 2      # 2 sim_cycle 당 CPU 1 cycle
  npu_period: 1      # 1 sim_cycle 당 NPU 1 cycle
  dram_period: 4     # 4 sim_cycle 당 DRAM 1 cycle
  noc_period: 2

npu:
  te_peak_flops: ...
  ve_width: ...
  dma_channel_count: ...
  sram_size_bytes: ...


실제 주파수(Hz)를 직접 쓰기보다는 상대적인 period 비율만 정의한다.

이렇게 하면 구조/병목/자원 활용 패턴 분석에는 충분한 정확도를 얻을 수 있다.

11. 구현 순서 제안

Tickable 베이스 클래스 구현

Simulator + 전역 loop 구현

CpuCore에 매우 단순한 tick 모델 적용 (예: 1 instr = 1 cycle 수준)

NpuSystem + DmaEngine + TensorEngine + VectorEngine tick 구현

MemorySystem + DramModel + NoC tick 구현

간단한 MatMul only workload로 end-to-end 실행

이후 LLM Kernel Execution Spec에 맞춰 QKV/Softmax/MLP 단계 확장