# xNPU ISA Specification & Design Document (Updated)

## 1. Overview
xNPU ISA(Custom RISC-V Extension)는 CPU가 NPU에게 작업을 지시하는 고급 인터페이스로서, 멀티테넌시, 컴파일러 최적화, 프로파일링, 가상화, 보안 측면에서 높은 이점을 제공한다. TE(Tensor Engine)·VE(Vector Engine)로 구성된 NPU 하드웨어에 대해 상위 레벨 추상화를 제공하고, 내부 스케줄링·DMA·타일링은 NPU MicroScheduler가 담당하도록 설계된다.

---

## 2. Design Principles
1. **ISA는 NPU 전체를 제어하는 상위 추상화**만 제공하며 TE/VE 구분은 숨긴다.
2. **Descriptor 기반 구조**를 통해 주소·shape·stride 등 메타데이터를 전달한다.
3. **TE/VE 실행 결정, 타일링, 배치 스케줄링은 MicroScheduler가 책임진다.**
4. **멀티테넌시·가상화·보안·컨텍스트 스위칭을 위해 CPU-MMU와 자연스럽게 통합된다.**
5. **ISA 명령은 비동기 job 기반이며 WAIT/BAR 명령을 통해 동기화한다.**

---

## 3. xNPU ISA Categories
| Category | Description |
|----------|-------------|
| Control | `XNPU.LAUNCH`, `XNPU.END`, `XNPU.WAIT`, `XNPU.BAR` |
| Tensor Compute(TE) | `XNPU.MATMUL`, `XNPU.GEMM` |
| Vector Compute(VE) | `XNPU.LAYERNORM`, `XNPU.SOFTMAX_1D`, `XNPU.ACT`, `XNPU.ROTARY_1D`, `XNPU.VOP` |
| Data Movement | `XNPU.LD`, `XNPU.ST` |

---

## 4. Example: VE-Oriented Instructions
### 4.1 LayerNorm
```
XNPU.LAYERNORM x5, rs1
```
Descriptor example:
```
struct xnpu_ln_desc {
  uint64_t src, dst;
  uint64_t gamma, beta;
  uint32_t hidden;
  float eps;
  uint32_t flags;
};
```

### 4.2 Softmax 1D
```
XNPU.SOFTMAX_1D x6, rs1
```
Descriptor example:
```
struct xnpu_softmax_desc {
  uint64_t src, dst;
  uint32_t vec_len, stride;
  uint32_t outer_count;
  uint32_t flags;
};
```

### 4.3 Rotary Embedding
```
XNPU.ROTARY_1D x7, rs1
```

### 4.4 Activation/VOP
```
XNPU.VOP x8, rs1
```
Descriptor includes `op_type`, `src`, `dst`, `len`, flags.

---

## 5. Multitenancy Advantages
### 5.1 Full OS-Level Resource Control
- ISA 명령은 CPU instruction 이므로 OS가 **스케줄링·격리·회계(accounting)** 가능.
- Process A/B가 각각 `XNPU.LAUNCH` 호출해도 kernel이 이를 큐잉·우선순위 조절 가능.

### 5.2 Context Switching Support
- CSR(xnpu_cmd_base, xnpu_token 등)을 저장·복원하여 **preemptive NPU scheduling** 가능.
- CMDQ 방식과 달리 NPU 내부 FSM 상태를 드라이버가 볼 수 없는 문제가 없음.

### 5.3 Memory Safety via MMU
- DMA 주소가 CPU MMU 보호 영역을 자동 상속 → **보안·격리·sandboxing 강화**.

### 5.4 Virtualization / Multi-Model Serving
- xNPU ISA는 하이퍼바이저가 trap/emulate 가능 → VM 환경에서도 안전하게 동작.

---

## 6. Compiler Advantages
### 6.1 Clean IR → ISA Mapping
| IR Node | xNPU ISA |
|---------|----------|
| MatMul | XNPU.MATMUL |
| LayerNorm | XNPU.LAYERNORM |
| Softmax | XNPU.SOFTMAX_1D |
| Activation | XNPU.ACT / XNPU.VOP |
| Rotary | XNPU.ROTARY_1D |

컴파일러는 TE/VE microkernel을 단순 조합하여 schedule 패스를 구성할 수 있음.

### 6.2 Fusion-Friendly
- LN→MatMul, Softmax→MatMul 등의 결합을 ISA 시퀀스로 표현 후
- MicroScheduler가 내부적으로 pipeline fusion 적용 가능.

### 6.3 Backend Flexibility
- shape-dependent 최적화(예: KV cache 길이에 따라 커널 선택) 가능.
- 다양한 타일 크기·DMA 정책을 ISA 변경 없이 지원.

---

## 7. Profiler Advantages
### 7.1 ISA-Level Timeline 가능
```
Cycle 1234: XNPU.LAYERNORM start
Cycle 1240: XNPU.MATMUL tile0 start
Cycle 1280: XNPU.MATMUL done(rd=6)
```
각 command의 시작·종료·stall·DMA·bank conflict 타임라인을 수집 가능.

### 7.2 Debugging & Bottleneck Analysis
- softmax stall, LN bottleneck, DRAM BW 부족 등 정확한 진단 가능.

### 7.3 Hardware–Simulator–Compiler 통합 프로파일 구조
- ISA abstraction이 동일하므로 HW 분석과 simulator trace 구조가 일치.

---

## 8. CPU–NPU Interface (ISA + MMIO)
### 8.1 Underlying Mechanism
- ISA는 CSR write + doorbell을 캡슐화한 것.
- MMIO-only, ISA-only, hybrid 모두 지원 가능.

### 8.2 Typical Sequence
1. CPU: descriptor를 DRAM에 작성
2. CPU: `XNPU.LAUNCH` → CSR(xnpu_cmd_base/len) write → doorbell
3. NPU MicroScheduler: cmd fetch → DMA → TE/VE pipeline
4. 완료 시 IRQ

---

## 9. Py-V Simulator Architecture (ISA + MMIO frontends)
```
PyVSimulator
  ├── CpuCore (Decode + CSR + MMIO)
  ├── Bus
  │     ├── MainMemory
  │     ├── NpuMmioDevice (MMIO frontend)
  ├── NpuDevice (Shared backend)
  │     ├── CommandQueue
  │     ├── MicroScheduler
  │     └── PipelineModel
  └── InterruptController
```
ISA frontend와 MMIO frontend 모두 `NpuDevice.enqueue()`를 호출하여 동일 backend로 연결된다.

---

## 10. Recommended Expansion
1. Attention Block ISA (optional)
2. MLP Block ISA (optional)
3. Graph Launch ISA
4. Kernel autotuning 기반 JIT selector

---


---

# **PRD_v1 – RISC-V + xNPU ISA 기반 NPU 시뮬레이터 Product Requirements Document**

## 1. **제품 개요 (Overview)**
본 제품은 **RISC-V + xNPU ISA 기반 NPU 성능/아키텍처 시뮬레이터**로서, CPU–NPU 인터페이스, xNPU ISA, TE/VE 파이프라인, DMA/메모리 모델, 멀티테넌시, 프로파일링까지 포함한 **엔드-투-엔드 AI 가속기 시스템 모델링**을 목표로 한다. LLM·Transformer 계열 모델의 end-to-end 성능 분석 및 알고리즘–하드웨어 협업 설계(Co-design)를 지원한다.

본 시뮬레이터는 Python 기반(Py-V 아키텍처)을 사용하며, NPU MicroScheduler, DMA, TE/VE, KV Cache, 타일링 정책, 메모리 계층 등을 정밀하게 모델링한다. 또한 xNPU ISA 또는 MMIO 기반의 NPU 실행 방식을 모두 지원한다.

---

## 2. **목적 (Purpose)**
- RISC-V 기반 SoC에서 **xNPU ISA 설계의 타당성·성능·멀티테넌시 가능성 검증**
- TE/VE 타일링 및 스케줄링이 **LLM 성능에 미치는 영향 분석**
- Memory/NoC/DMA 병목을 정량 분석
- ISA 설계–컴파일러–마이크로스케줄러–메모리 모델을 하나의 프레임워크에서 통합
- 실제 하드웨어 설계를 위해 필요한 구조적 통찰(TE/VE 분할, SRAM banking, DRAM BW 요구 등) 제공

---

## 3. **기능 요구사항 (Functional Requirements)**

### 3.1 CPU–NPU 인터페이스
- RISC-V Custom Opcode 기반 xNPU ISA 지원
- MMIO + doorbell 방식 동시 지원
- CSR(xnpu_cmd_base/len/status/token 등) 모델링
- RISC-V Py-V CPU pipeline과 자연스럽게 연동

### 3.2 xNPU ISA 지원 범위
- Control: `LAUNCH`, `WAIT`, `BAR`
- Tensor Ops(TE): `MATMUL`, `GEMM`
- Vector Ops(VE): `LAYERNORM`, `SOFTMAX_1D`, `ROTARY_1D`, `ACT`, `VOP`
- Descriptor 기반 정보 전달
- Token 기반 비동기 job 모델

### 3.3 NPU MicroScheduler
- Descriptor fetch → DMA plan → TE/VE execution → Writeback
- TE/VE pipeline 병렬화 모델링
- DMA–Compute Overlap 관리
- Block-level fusion (optional)
- Command dependency graph 처리

### 3.4 Memory/DMA/NoC 모델
- DRAM 읽기/쓰기 지연 및 BW 제한
- Scratchpad 설계 (bank conflict, multi-port, latency)
- DMA 채널 모델: concurrency, burst, alignment
- KV Cache 관리 (LLM용)

### 3.5 TE (Tensor Engine)
- GEMM 파이프라인 모델: tile fetch, MAC unit latency, pipeline depth
- Activation/bias fusion 지원(옵션)
- PSUM merge pipeline 모델

### 3.6 VE (Vector Engine)
- LN/RMSNorm/Softmax/Rotary/Activation 등 1D/2D vector ops 지원
- 포인터 기반 chunk/stride 처리
- TE와 병렬 실행 가능

### 3.7 시뮬레이터 실행 엔진
- cycle-accurate 또는 near-cycle 모델
- CPU/NPU 각각 독립 tick + global sync step
- Interrupt path(Plic-like) 모델링

### 3.8 프로파일러
- ISA-level event timeline 생성
- DMA/TE/VE/Barrier 도식화
- Gantt 차트 스타일 시각화
- JSON 로그 export
- Roofline-like utilization 분석

---

## 4. **비기능 요구사항 (Non-Functional Requirements)**

### 4.1 정확도
- Cycle-level에서 80~90% accuracy (모델링 수준에 따라 조절)
- DMA latency, pipelining, overlap을 실제 하드웨어 유사하게 반영

### 4.2 확장성
- xNPU ISA 확장 가능: Attention Block 등 추가 가능
- 파이프라인/메모리 모듈 교체 가능
- 다양한 LLM 모델 적용 가능 (BERT, GPT, LLaMA, Mamba-RNN 기반 등)

### 4.3 유지보수성
- Python 모듈형 구조
- TE/VE/MicroScheduler/Memory를 독립 모듈로 구성
- Config-driven 설계 (JSON/YAML)

### 4.4 실행 속도
- 시뮬레이션 1 step < 1ms 성능 목표
- LLM block-level simulation 1~10초 내 수행 목표

---

## 5. **시스템 아키텍처 요구사항**
- Py-V RISC-V CPU 모델 + NPU 모델 통합
- NPUDevice: CommandQueue, MicroScheduler, TE, VE, DMA, SRAM, DRAM
- Bus: MainMemory + NpuMmioDevice
- Interrupt Controller: NPU → CPU 이벤트 처리

---

## 6. **멀티테넌시 요구사항**
- xNPU ISA 기반 job accounting
- Process별 NPU context 유지
- CSR 저장·복원으로 preemption 지원
- MMU 기반 보호 적용
- Multi-model serving 지원

---

## 7. **컴파일러 연동 요구사항**
- IR → xNPU ISA lowering 가능 구조
- TE/VE kernel 조합 기반 schedule passes
- descriptor 기반 metadata pipeline
- fusion pass 정의 (LN→MatMul, Softmax→MatMul 등)

---

## 8. **프로파일러 요구사항**
- ISA-level operation timeline
- DMA/TE/VE overlap analysis
- stall reason 분석 (softmax stall, LN stall, DRAM BW shortage)
- export format(JSON/CSV)

---

## 9. **입출력 요구사항**
### 입력
- ONNX/PyTorch exported graph
- xNPU descriptor stream
- RISC-V binary (ISA-based execution)
- Config JSON (SRAM, BW, DMA channels 등)

### 출력
- Timeline plot
- Gantt chart
- Performance summary(JSON)
- DRAM BW/FLOPs/Utilization 보고서

---

## 10. **초기 개발 범위 (MVP Scope)**
1. `XNPU.LAUNCH`, `XNPU.MATMUL` + `XNPU.LAYERNORM` + `XNPU.VOP`
2. MicroScheduler 기본 구조
3. DMA/Compute overlap 기본 지원
4. Py-V RISC-V 통합 (ISA + MMIO)
5. Memory/SRAM 모델 baseline
6. 간단한 GPT/Transformer block 실행
7. Timeline/Gantt 출력

---

## 11. **로드맵**
### 1단계 (MVP)
- TE/VE 단순 모델
- LN/GEMM/ACT 중심
- xNPU ISA 최소 세트
- Gantt/Timeline

### 2단계
- Softmax/Rotary/RMSNorm 추가
- MicroScheduler 고도화
- Fusion 지원
- DRAM/NoC 병목 모델링

### 3단계
- Attention block ISA
- Graph Launch ISA
- Multi-tenancy preemption
- Detailed power/performance model

---

## 12. **승인 기준 (Acceptance Criteria)**
- 주어진 LLM Layer descriptor를 파싱하여 TE/VE/DMA 수행 가능
- ISA 기반 & MMIO 기반 인터페이스 모두 동작
- Gantt chart에서 TE/VE/DMA overlap 확인 가능
- DRAM BW 제한을 반영한 latency 변화 재현
- LN → GEMM → ACT 파이프라인을 순서대로 또는 overlap로 실행 가능
- JSON 로그가 컴파일러/프로파일러에서 재활용 가능

---
