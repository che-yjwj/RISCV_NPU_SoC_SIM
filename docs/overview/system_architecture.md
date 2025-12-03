# NPU Simulator & Offline Compiler  
System Architecture Specification (Full Version)

**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->  
**Owner:** System Architect  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적 (Purpose)

이 문서는 정적 스케줄 기반 NPU 시뮬레이터 & 오프라인 컴파일러 플랫폼의 전체 시스템 아키텍처를 정의한다.  
본 아키텍처는 ONNX 기반 AI 모델을 입력으로 받아, 다음을 지원하도록 설계되었다.

- 오프라인 컴파일러를 통한 IR 변환, 타일링, 스케줄링, CMDQ 생성  
- CMDQ 기반 NPU 시뮬레이터를 통한 실행 시간·메모리·자원 사용률 예측  
- Multi-TE/VE 구조의 병렬 처리 모델  
- Mixed-precision quantization 및 bitwidth 기반 memory-accurate 분석  
- LLM-friendly 구조 (KV cache, attention tile, load-balance 등)  
- 시각화(Visualization): Gantt, bandwidth heatmap, utilization map 등  

본 문서는 코드 구현 이전에 반드시 참조하는 최상위 아키텍처 스펙을 제공한다.

---

## 2. 아키텍처 상위 개요 (High-Level Overview)

전체 시스템은 다음 4개의 메인 모듈로 구성된다.

- Host CPU (RISC-V)  
- Offline Compiler (ONNX → IR → CMDQ)  
- NPU Simulator Core (Cycle-based)  
- Visualization / Profiler  

아키텍처 전체 구조는 아래와 같다.

```text
+-------------------------------------------------------+
|                      Host CPU (RISC-V)                |
|  - MMIO/CSR                                           |
|  - NPU Launch                                         |
|  - Test Harness / Profiling Controller                |
+----------------------------+--------------------------+
                             |
                             V
+-------------------------------------------------------+
|                   Offline Compiler                    |
|  - ONNX Loader                                        |
|  - IR Builder                                         |
|  - Quantization Annotator (W/A/KV-bit)                |
|  - Tiling Planner                                     |
|  - SPM Allocator                                      |
|  - Static Scheduler                                   |
|  - CMDQ Generator                                     |
+----------------------------+--------------------------+
                             |
                             V
+-------------------------------------------------------+
|                NPU Simulator Core (Cycle-based)       |
|  - Control FSM                                        |
|  - CMDQ Executor                                      |
|  - DMA Engine                                         |
|  - Multi TE (Tensor Engines)                          |
|  - Multi VE (Vector Engines)                          |
|  - SPM/BUS/DRAM/NoC Model                             |
|  - Trace Engine (timeline, bw, util)                  |
+----------------------------+--------------------------+
                             |
                             V
+-------------------------------------------------------+
|              Visualization & Profiler                 |
|  - Gantt Timeline                                     |
|  - Bandwidth Heatmap                                  |
|  - Engine Utilization                                 |
|  - Quantization Impact Plot                           |
|  - Exporter (PNG/SVG/JSON)                            |
+-------------------------------------------------------+
```

---

## 3. 설계 철학 (Design Philosophy)

### 3.1 Spec-Driven Development

본 시스템은 모든 기능이 Spec 문서(IR/ISA/Timing/Trace)에 의해 정의된 방식으로 동작한다.  
코드는 스펙을 구현한 결과여야 하며, 스펙이 항상 우선한다.

### 3.2 정적 스케줄 기반 CMDQ 모델

Mobile/Edge NPU는 일반적으로 런타임 스케줄러를 두지 않고,  
오프라인에서 생성된 정적 스케줄링 결과를 CMDQ 형태로 실행한다.

이에 따라:

- 실행 중 그래프 구조/flow는 바뀌지 않는다.  
- Control FSM은 단순하고 예측 가능하다.  
- 성능 분석 및 병목 파악이 용이하다.  

### 3.3 Cycle-accurate보다는 Resource-accurate

목표는 정확한 cycle-level RTL 시뮬레이터가 아니라,  
NPU 구조의 병목/자원 사용률/메모리 traffic을 정확히 반영하는 분석용 Simulator다.

정확성 목표:

- latency 예측 오차 ±10~15%  
- bandwidth/traffic 패턴 분석 정확도 높음  
- TE/VE/DMA busy ratio를 직관적으로 파악 가능  

### 3.4 Multi-Engine 구성 지원

- TE ≥ 2, VE ≥ 2  
- tile-level 병렬 처리 스케줄링  
- LLM attention head parallelism 반영 가능  

### 3.5 Bitwidth-driven Memory Model

- FP32 → INT8 → INT4 → INT2로 줄어들수록  
  메모리 transaction이 줄어드는 구조를 정밀하게 반영  
- Layer별로 Weight/Activation/KV bitwidth를 각각 설정 가능  

---

## 4. 주요 모듈 상세 (Module-Level Architecture)

### 4.1 Host CPU (RISC-V 기반)

**역할**

- 컴파일러가 생성한 CMDQ를 NPU에 전달  
- CSR/MMIO로 NPU Control FSM 제어  
- test harness, benchmark runner 제공  
- 전체 실행 로그 수집  

**입력/출력**

- 입력: CMDQ 메모리 주소  
- 출력: execution trace, profiling 결과  

**NPU launch 예시**

```c
write_csr(NPU_CMDQ_BASE, addr);
write_csr(NPU_START, 1);
wait(NPU_DONE);
```

### 4.2 Offline Compiler

Offline Compiler는 그래프를 완전히 정적 분석하여 CMDQ를 생성한다.

**구성 요소**

1) **ONNX Loader**  
   - opset 변환  
   - weight/activation shape 추출  
   - graph normalization  

2) **IR Builder**  
   - 내부 IR 생성 (LayerIR / TensorIR)  
   - qbits annotation 가능  

3) **Quantization Annotator**  
   - W/A/KV bitwidth을 레이어별로 식별  
   - mixed precision 정책 적용  

4) **Tiling Planner**  
   - SPM 용량 기반 tile 크기 결정  
   - TE/VE 병렬 구조 반영  
   - LLM attention tile 가능  

5) **SPM Allocator**  
   - tile 단위 메모리 공간 배치  
   - multi-bank conflict 최소화  

6) **Static Scheduler**  
   - TE/VE/DMA 의존성 기반 스케줄 생성  
   - multi-TE/VE load-balance 고려  
   - barrier 삽입  

7) **CMDQ Generator**  
   - 모든 scheduling 결과를 CMDQ로 serialize  
   - DMA/TE/VE/BARRIER 명령 생성  
   - 레이어별 → tile별 → engine별 명령 스트림 구성  

### 4.3 NPU Simulator Core

Simulator는 cycle 기반 글로벌 loop를 중심으로 동작한다.

**핵심 요소**

1) **Control FSM**  
   - IDLE → FETCH → DECODE → ISSUE → WAIT → NEXT  
   - CMDQ 단위 실행 관리  

2) **CMDQ Executor**  
   - 엔진별 job queue 삽입  
   - 의존성(barrier) 처리  
   - tile-level 디스패치  

3) **DMA Engine**  
   - DRAM↔SPM 데이터 이동  
   - bitwidth 기반 transaction 계산  
   - bus contention / burst 모델 포함  

4) **Tensor Engine (TE)**  
   - matmul/GEMM tile 처리  
   - MAC/cycle 기반 latency  
   - pipeline depth 반영  

5) **Vector Engine (VE)**  
   - layernorm/softmax/gelu/RMSNorm 등 처리  
   - SIMD lanes 기반 latency  
   - reduction latency 포함  

6) **Memory / Bus Model**  
   - SPM multi-bank  
   - port conflict  
   - DRAM bandwidth 모델  
   - NoC arbitration 정책  

7) **Trace Engine**  
   - timeline(start/end)  
   - bandwidth(bytes/timestep)  
   - utilization(%)  
   - SPM conflict map  

### 4.4 Visualization & Profiler

**지원 뷰**

- Gantt Timeline  
- DRAM/Bus Bandwidth Heatmap  
- SPM Bank Conflict Map  
- TE/VE Utilization  
- Quantization Impact Graph  

**Export Format**

- JSON  
- PNG/SVG  
- CSV  

---

## 5. 데이터 플로우 (Dataflow Architecture)

전체 데이터 플로우는 아래와 같다.  
자세한 단계별 설명과 LLM/Prefill/Decode 시나리오는 `docs/overview/dataflow_overview.md`에서 다룬다.

```text
[ONNX Model]
      ↓
[IR Builder] — add QConfig/W/A/KV bits
      ↓
[Tiling Planner]
      ↓
[SPM Allocator]
      ↓
[Static Scheduler]
      ↓
[CMDQ Generator]
      ↓
[Host CPU: NPU Launch]
      ↓
[NPU Simulator Core: Cycle Loop]
      ↓
[Trace Engine]
      ↓
[Visualization]
```

모든 단계는 명확한 입력/출력 데이터 구조를 가지며,  
IR/ISA/Timing/Quant/Trace 스펙(`docs/spec/**`)에 의해 정의된 형식을 따른다.  
Dataflow 관점에서의 산출물/연결 관계는 `dataflow_overview.md`에서 보완적으로 설명한다.

---

## 6. NPU 모델의 범위 (Modeling Scope)

본 시뮬레이터는 다음을 정확하게 모델링한다.

- tile-level compute latency  
- DMA burst latency  
- bus contention  
- SPM bank conflict  
- TE/VE 병렬 처리 구조  
- bitwidth-driven memory traffic  
- static scheduling structure  
- KV cache 성장에 따른 DRAM traffic 증가  

다만 실제 silicon-level 정확도(파이프라인 hazard, stall cycle 완벽 재현)는 목표가 아니다.  
자원 사용률 및 병목을 분석하는 수준의 정확성을 목표로 한다.

---

## 7. 설계 제약 및 가정 (Assumptions)

- 런타임 dynamic graph는 고려하지 않는다.  
- 모든 스케줄은 offline에서 완성된다.  
- NPU 내부에 CPU/firmware는 없고, Control FSM만 존재한다.  
- 모든 엔진은 한 cycle 단위 업데이트된다.  
- 실 칩 DRAM controller의 미세한 timing은 모델링하지 않음  
  (대역폭/버스트 기반만 반영).  

---

## 8. 확장성 (Extensibility)

본 아키텍처는 다음을 고려하여 설계되었다.

- **LLM-oriented 확장**
  - head parallelism  
  - KV cache compression  
  - sliding-window attention  
  - rotary positional embedding 처리  

- **Hardware-oriented 확장**
  - 새로운 opcode 추가  
  - TE/VE 개수 변경  
  - sparsity engine 추가 가능  
  - compression engine 추가 가능  

- **Compiler-oriented 확장**
  - MLIR backend 연동  
  - auto-tuning 기반 tile optimizer  

---

## 9. 결론 (Summary)

본 문서는 NPU Simulator & Offline Compiler 프로젝트의 최상위 아키텍처 스펙이며,  
다른 모든 Spec 문서(IR/ISA/Timing/Quantization)와 Design 문서(TDD)는  
이 문서를 기반으로 작성·업데이트되어야 한다.

이 문서를 통해 다음을 보장한다.

- 기능 경계 명확  
- 스케줄링/타이밍 모델 일관성  
- trace 기반 병목 분석 가능  
- 확장 가능한 구조  
- 완전한 Spec-driven 개발 가능  
