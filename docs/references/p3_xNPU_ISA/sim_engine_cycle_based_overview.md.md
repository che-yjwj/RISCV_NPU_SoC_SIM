docs/overview/sim_engine_cycle_based_overview.md
# 전역 CPU Cycle Loop 기반 Cycle-Level 시뮬레이터 개요

## 1. 목적

본 문서는 RISC-V + xNPU ISA 기반 NPU 시뮬레이터에서 **전역 CPU cycle loop 하나로 통일된 cycle-based 시뮬레이션 엔진**의 개념을 설명한다.

이 시뮬레이터의 목표는 다음과 같다.

- 정확한 절대 시간/클럭 재현보다는  
  **어떤 지점이 병목인지, 각 자원이 얼마나 효율적으로 쓰이는지**를 분석
- CPU, NPU(TE/VE), DMA, DRAM, NoC, SRAM 등 다양한 하드웨어 컴포넌트를  
  **하나의 전역 시뮬레이션 cycle(sim_cycle)** 위에서 통합적으로 모델링
- 코드 구조를 단순화하여 **유지보수성과 이해 용이성**을 극대화

즉, 이 시뮬레이터는 “정확한 gate-level 타이밍 검증 도구”가 아니라  
**성능/구조 분석용 아키텍처 연구 도구**를 지향한다.

---

## 2. 기본 개념: 전역 sim_cycle

### 2.1 sim_cycle 정의

- 시뮬레이터는 **하나의 정수 카운터 `sim_cycle`**을 사용하여 시간의 진행을 표현한다.
- `sim_cycle`은 추상적인 “공통 시간 단위”로,  
  실제 하드웨어의 CPU/NPU/DRAM 클럭과 1:1로 대응되지 않는다.
- 중요한 것은:
  - **모든 컴포넌트가 이 `sim_cycle` 축 위에서 동작한다**는 점
  - 각 컴포넌트는 자신의 속도 특성을 `sim_cycle` 단위 latency로 환산하여 사용한다.

### 2.2 전역 loop

시뮬레이터의 메인 루프는 다음과 같이 정의된다.

```python
sim_cycle = 0
while sim_cycle < max_cycles and not done:
    cpu.tick(sim_cycle)
    npu.tick(sim_cycle)
    mem.tick(sim_cycle)
    noc.tick(sim_cycle)
    irq_ctrl.tick(sim_cycle)
    profiler.tick(sim_cycle)
    sim_cycle += 1


tick()이 한 번 호출될 때마다 sim_cycle이 정확히 1 증가한다.

모든 모듈은 tick(sim_cycle) 안에서 자신의 상태를 1 step 업데이트한다.

3. 멀티 클럭 도메인 모델링: period 개념

현실 하드웨어에서는 CPU, NPU, DRAM, NoC가 서로 다른 클럭 도메인으로 동작한다.

예시:

CPU: 1.0 GHz

NPU Core(TE/VE): 2.0 GHz

DRAM: 0.5 GHz

NoC: 1.5 GHz

하지만 시뮬레이터에서는 복수의 클럭을 직접 흉내 내지 않고,
각 블록에 **“tick 주기(period)”**를 부여하는 방식으로 모델링한다.

3.1 period / local_phase 개념

각 모듈은 다음 필드를 가진다.

period: 해당 모듈의 1 local cycle이 몇 sim_cycle마다 발생하는지를 나타내는 정수

local_phase: 현재 모듈이 몇 sim_cycle째인지 추적하는 카운터

예:

class CpuCore:
    period = 2   # 2 sim_cycle 당 CPU 1 cycle
    local_phase = 0

class NpuDevice:
    period = 1   # 1 sim_cycle 당 NPU 1 cycle

class DramModel:
    period = 4   # 4 sim_cycle 당 DRAM 1 cycle


tick 시 동작:

def tick(self, sim_cycle):
    self.local_phase += 1
    if self.local_phase < self.period:
        return  # 이번 sim_cycle에는 실제 local cycle이 발생하지 않는다.
    self.local_phase = 0
    self._advance_one_local_cycle()


즉:

sim_cycle은 모든 모듈에 대해 공통

각 모듈은 자기 period에 맞춰 일정 간격으로만 실제 local cycle을 진행한다.

이를 통해 multi-clock 시스템을 단일 sim_cycle 축 위에서 표현할 수 있다.

4. Latency 모델링

각 컴포넌트의 latency는 다음과 같이 모델링한다.

먼저, 자기 도메인 기준 latency를 계산한다.

예: TE GEMM tile latency = L_te_cycles

예: DRAM access latency = L_dram_cycles

이를 sim_cycle 기준 latency로 변환:

L_sim = L_te_cycles * te.period

L_sim = L_dram_cycles * dram.period

모듈 내부에서 remaining_cycles 또는 유사 카운터로 관리한다.

예:

te_latency_sim = te_latency_te_cycles * self.period
job.remaining_cycles = te_latency_sim


tick 시:

if job.remaining_cycles > 0:
    job.remaining_cycles -= 1
    if job.remaining_cycles == 0:
        job.done = True
        # MicroScheduler에 completion 알림


→ 이 방식으로 각 도메인의 속도 차이를
period와 latency 변환을 통해 sim_cycle에서 표현할 수 있다.

5. 정확도 vs 단순성 트레이드오프

본 설계는 다음과 같은 판단에 기반한다.

목표:

LLM/Transformer workload에서

어디가 병목인가?

TE/VE/DMA/DRAM이 얼마나 바쁘게 일하는가?

DMA–Compute–SRAM의 overlap이 어떤 패턴으로 일어나는가?

정확한 “절대 시간(ns)”이나 완전한 cycle-accurate HW 검증이 목표가 아니다.

따라서:

클럭 주파수를 실제 값 그대로 맞추기보다는,

“CPU보다 NPU가 몇 배 빠른가”

“DRAM access는 대략 CPU 몇 cycle 수준인가”
와 같이 상대적인 속도 관계를 유지하는 것이 더 중요하다.

모델이 단순할수록:

코드가 쉬워지고,

병목/자원 활용률 분석의 흐름을 이해하기가 쉬워진다.

6. Event-driven vs Cycle-based

기존 문서에서는 MicroScheduler/DMA/TE/VE/Profiler에 대해
event-driven 구현도 가능하도록 설계했지만,
최종 구현에서는 다음을 채택한다.

전역 sim_cycle loop 방식 (cycle-based)

모든 모듈은 tick() 인터페이스로 통일

이벤트/완료 조건은 내부 카운터 및 상태머신을 통해 표현

이는:

코드 구조를 통일하고,

디버깅/리팩토링 시 이해하기 쉬운 형태를 유지하며,

LLM 성능 분석에 충분한 정확도를 제공한다.

7. 기존 스펙들과의 관계

이 문서는 다음 문서들과 결합하여 사용된다.

xNPU ISA & Design Spec

PRD_v1

TDD(Py-V Integration)_v1

MicroScheduler Spec_v1

Memory/NoC Model Spec_v1

LLM Kernel Execution Spec_v1

Profiler & Trace Format Spec_v1

위 문서들이 정의하는 기능/인터페이스/구조는 그대로 유지하되,
시뮬레이션 시간 축 구현을 “전역 sim_cycle 기반 tick() 모델”로 구체화한 것이 본 문서의 역할이다.