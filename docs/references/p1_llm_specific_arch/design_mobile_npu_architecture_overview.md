# `design_mobile_npu_architecture_overview.md`

# 📘 `design_mobile_npu_architecture_overview.md`가 어떤 문서인가?

이 문서는 다음을 설명합니다:

### 1. **모바일 NPU가 서버용 NPU와 어떻게 다른지**

- 동적 스케줄링 없음
- 정적 스케줄링 기반
- 메모리 계층(Shared SRAM, System DRAM, Weight Compression 등)
- NPU의 TE/VE 구조
- ISP/디스플레이/센서 허브와의 연동
- 전력/발열 기반 제약

---

### 2. **삼성/퀄컴/애플 모바일 NPU의 공통 아키텍처 패턴**

예:

- Apple ANE → fully static graph execution + tile-based DMA
- Qualcomm Hexagon → HVX/VTCM 기반 정적 TCM map + static tiling
- Samsung NPU → fixed scheduling + static dual-engine TE/VE structure

이들의 공통점:

> “복잡한 동적 스케줄링을 하드웨어에서 하지 않는다.
> 
> 
> 모든 스케줄링은 컴파일러가 책임지고,
> 
> NPU는 정적으로 만들어진 command stream을 반복 실행하는 기계이다.”
> 

---

### 3. **당신의 시뮬레이터가 모사해야 하는 모바일 NPU 구조의 핵심**

- Static Graph Compiler
- Memory Planner
- Tile Scheduler
- NPU ISA(Command Stream)
- Prefill/Decode static separation
- Fixed DMA choreography
- TE/VE pipeline
- Clock/latency/power 모델
- Weight compression/quantization
- SRAM bank conflict 모델

---

### 4. **NPU 내부 구조 (Block Diagram)**

문서에서는 아래 같은 구조를 정리하게 됨:

```
          ┌───────────────────────┐
          │     RISC-V CPU        │
          │  (Command Dispatcher) │
          └──────────┬────────────┘
                     │
          ┌──────────▼───────────┐
          │       NPU CORE       │
          │ ┌────────┬────────┐ │
          │ │   TE    │   VE   │ │
          │ └────────┴────────┘ │
          │ ┌──────────────────┐ │
          │ │      DMA         │ │
          │ └──────────────────┘ │
          │ ┌──────────────────┐ │
          │ │   SRAM BANKS     │ │
          │ └──────────────────┘ │
          └──────────┬──────────┘
                     │
        System DRAM (Weights / KV Cache / Activations)

```

---

### 5. **정적 스케줄링 기반 전체 실행 플로우**

문서에서 아래와 같이 구조화됩니다:

1. Graph Lowering
2. Static Tiling
3. Static Memory Planning (SRAM allocation)
4. Static Scheduling
5. Command Stream Generation
6. Runtime Execution
7. Timing Model
8. Power Estimate

이 부분을 **당신의 전체 시뮬레이터 메인 플로우의 기준**으로 삼습니다.

---

### 6. **Prefill/Decode 정적 분리의 아키텍처적 위치**

이 문서는 Prefill/Decode 자체를 설명하는 것이 아니라,

“Prefill Graph와 Decode Graph가 어디에서 Static Scheduling 되는지”를 설명합니다.

즉:

```
Graph Compiler:
    Prefill Graph → Static Schedule → Prefill Cmd Stream
    Decode Graph → Static Schedule → Decode Cmd Stream

```

NPU는 단순히:

```
Execute(PrefillCmd)
Execute(DecodeCmd Loop N times)

```

---

### 7. **메모리 계층**

이 문서에서는 다음 구조를 설명합니다:

- on-chip SRAM의 크기 / bank 수
- system DRAM bandwidth
- weight compression
- KV Cache layout
- DMA 패턴
- latency model

이러한 요소는 시뮬레이터가 정확한 timing/power estimation을 하기 위해 필요함.

---

### 8. **정적 NPU ISA(Command Stream) 개념**

문서는 다음을 정리합니다:

- TE/VE 명령
- DMA 명령
- LOOP 명령
- Prefill/Decode 페이즈 전환 명령
- Stall/Wait 규칙
- Event 없음 (dynamic scheduling 없음)

이는 시뮬레이터가 실행할 **고정된 명령 목록**의 사양을 정의함.

---

### 9. **모바일 환경에서의 제약**

문서에는 다음 제약도 서술될 것:

- 전력 제한 (thermal envelope)
- 메모리 대역폭 제한
- 프레임 시간 제한 (예: 카메라 inference 16ms 조건)
- 모바일 배터리 기반 성능/전력 트레이드오프

따라서 Graph는 static하게 만들어야 하고, runtime scheduling은 원천적으로 금지됨.

---

# 📌 정리:

### `design_mobile_npu_architecture_overview.md`는

모바일 NPU 전체 시스템 구조 + 정적 스케줄링 기반 실행 모델을 설명하는

**최상위 아키텍처 개요 문서**입니다.

이 문서를 기반으로 다음 서브 문서를 가지게 되죠:

- `design_static_memory_planner.md`
- `design_static_tile_scheduler.md`
- `design_npu_cmd_stream_format.md`
- `design_llm_prefill_decode_static.md`
- `design_mobile_power_model.md`

즉, 전체 문서 트리에서 최상단 ROOT 문서 역할을 수행합니다.