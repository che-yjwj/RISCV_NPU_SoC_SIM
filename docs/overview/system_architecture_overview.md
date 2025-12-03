# System Architecture Overview (One-Page)
**Path:** `docs/overview/system_architecture_overview.md`  
**Version:** v1.0  
**Status:** Draft  
<!-- status: draft -->
**Owner:** System Architect  
**Last Updated:** 2025-12-03  

---

## 1. 목적 (Purpose)

이 문서는 `RISCV_NPU_SoC_SIM`의 전체 시스템 아키텍처를  
**한 페이지에서 빠르게 파악**하기 위한 개요 문서이다.

- Host CPU, Offline Compiler, NPU Simulator Core, Visualization 모듈이  
  어떤 역할을 갖고 어떻게 연결되는지 high-level로 설명한다.
- 세부 구조/타이밍/데이터플로우는 다음 문서에서 다룬다.
  - `docs/overview/system_architecture.md` (풀 버전 아키텍처 스펙)
  - `docs/overview/dataflow_overview.md` (ONNX→IR→CMDQ→Simulator 데이터 플로우)
  - `docs/overview/module_responsibilities.md` (모듈별 책임/경계)

---

## 2. 대상 독자 (Target Reader)

- 레포를 처음 접하는 신규 기여자  
- 전체 그림을 빠르게 공유해야 하는 리뷰어/PM/리서처  
- 세부 스펙을 읽기 전에 “이 시스템이 무엇을 하는지”를 단번에 이해하고 싶은 사람

---

## 3. 상위 구성요소 (Top-Level Components)

시스템은 크게 네 개의 상위 컴포넌트로 나뉜다.

1. **Host CPU (RISC-V SoC)**  
   - CMDQ와 설정(config)을 NPU에 전달하고, 실행을 시작/종료한다.  
   - 테스트 하네스 및 벤치마크 런처 역할도 수행한다.  
   - AXI/메모리 맵을 통해 NPU 레지스터(CSR/MMIO)에 접근하며, DRAM은 CPU/NPU가 공유하는 구조를 가정한다.

2. **Offline Compiler**  
   - ONNX 모델을 입력으로 받아, 내부 IR → Tiling → SPM 계획 → Static Schedule → CMDQ를 생성한다.  
   - 결과물(CMDQ, 메타데이터)은 NPU Simulator의 유일한 입력이 된다.

3. **NPU Simulator Core (Cycle-Based)**  
   - CMDQ를 기반으로 TE/VE/DMA/SPM/DRAM/NoC를 cycle 단위로 시뮬레이션한다.  
   - Timing/Quantization/Memory 모델을 적용해 latency, bandwidth, utilization을 계산한다.

4. **Visualization / Profiler**  
   - Trace를 이용해 timeline, bandwidth heatmap, utilization, memory traffic 등을 시각화한다.  
   - 성능 회귀/튜닝/아키텍처 비교에 사용된다.

각 컴포넌트의 자세한 구조와 인터페이스는 `system_architecture.md`를 참고한다.

---

## 4. 아키텍처 한눈에 보기 (Text Diagram)

```text
[Host CPU (RISC-V)]
    - MMIO/CSR, NPU Launch
    - DRAM Controller / SoC Interconnect
          |
          v
[Offline Compiler]
    - ONNX Loader / IR Builder
    - Quantization Annotator
    - Tiling Planner / SPM Allocator
    - Static Scheduler
    - CMDQ Generator
          |
          v
[NPU Simulator Core]
    - Control FSM (CMDQ Executor)
    - DMA / TE / VE Engines
    - SPM / DRAM / NoC Models
    - Trace Engine
          |
          v
[Visualization & Profiler]
    - Timeline / BW Heatmap / Utilization
```

이 다이어그램은 `system_architecture.md`의 상세 블록 다이어그램을  
텍스트 기반으로 축약한 형태이다.

---

## 5. 관련 문서와 읽기 순서

이 문서를 다 읽었다면, 다음 순서를 추천한다.

1. `docs/overview/system_architecture.md` — 각 구성요소와 설계 철학을 자세히 이해  
2. `docs/overview/dataflow_overview.md` — ONNX→IR→TileGraph→CMDQ→Simulator→Trace 흐름 파악  
3. `docs/overview/module_responsibilities.md` — 모듈별 책임/경계(Does/Does Not) 확인  

그 후에는 `docs/spec/ir/*.md`, `docs/spec/isa/*.md`, `docs/spec/timing/*.md`를 읽으며  
관심 있는 영역(컴파일러/시뮬레이터/메모리/Trace)의 세부 내용을 따라가면 된다.

---

## 6. 향후 확장 아이디어

- 대표 LLM 블록(예: 단일 Transformer layer)을 기준으로  
  Host CPU → Offline Compiler → NPU Simulator → Trace로 이어지는  
  end-to-end 시나리오를 간단한 스토리라인으로 추가할 수 있다.
