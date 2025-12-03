# Memory & NoC Overview
**Path:** `docs/overview/memory_noc_overview.md`  
**Version:** v1.0  
**Status:** Draft  
<!-- status: draft -->
**Owner:** System Architect  
**Last Updated:** 2025-12-03  

---

## 1. 목적 (Purpose)

이 문서는 `RISCV_NPU_SoC_SIM`에서 모델링하는 **메모리 계층 및 Bus/NoC 구조**를  
한 페이지에서 요약한다.

- DRAM, Bus/NoC, SPM(Scratchpad), DMA Engine 간 관계를 high-level로 설명한다.  
- 세부 타이밍/용량/컨텐션 모델은 각 Timing/Design 스펙에서 다룬다.

관련 문서:

- 시스템 관점: `docs/overview/system_architecture.md`  
- 타이밍 스펙: `docs/spec/timing/dma_timing_spec.md`, `spm_model_spec.md`, `bus_and_noc_model.md`  
- 설계 문서: `docs/design/dma_engine_design.md`, `spm_allocator_design.md`, `cycle_loop_design.md`

---

## 2. 메모리 계층 구조 (Memory Hierarchy)

```text
[DRAM]
   │  (High capacity, high latency)
   ▼
[Bus / NoC]
   │  (Bandwidth / arbitration / contention)
   ▼
[SPM (Scratchpad Memory)]
   │  (Multi-bank, low latency, limited size)
   ▼
[TE / VE Engines]
```

- **DRAM**: 모델 전체 파라미터/activation/KV cache의 대부분이 상주하는 외부 메모리.  
- **Bus/NoC**: DRAM↔NPU 사이 트래픽을 중개, channel/burst/arbiter 모델을 가짐.  
- **SPM**: tile-level compute를 위해 필요한 working set을 담는 on-chip scratchpad.  
- **TE/VE**: SPM에서 데이터를 읽어 연산을 수행하고, 결과를 다시 SPM/DRAM에 기록.

SoC 관점에서는, DRAM은 CPU와 NPU가 공유하는 외부 메모리이며,  
CPU는 명령/제어/테스트 하네스를 담당하고, NPU는 tile-level 데이터 이동과 연산을 담당한다.

---

## 3. DMA & SPM 관점 Dataflow

1. DMA 엔진은 CMDQ의 `DMA_LOAD_TILE` / `DMA_STORE_TILE` 명령을 읽고,  
   - DRAM 주소/크기/bitwidth에 따라 버스트 transaction을 생성한다.  
2. Bus/NoC 모델은 DMA 채널/TE/VE/다른 트래픽 간 **대역폭 공유와 컨텐션**을 모델링한다.  
3. SPMAllocator는 tile별 IFM/WGT/OFM/KV 데이터를 어느 bank/offset에 둘지 결정하고,  
   - bank conflict, alignment, capacity를 고려해 mapping한다.  
4. Timing 스펙에서는:
   - DRAM: tRCD/tCL/bank conflict penalty  
   - SPM: bank/port conflict, access latency  
   - Bus/NoC: link bandwidth, arbitration 정책  
   을 통해 전체 latency와 traffic 패턴을 근사한다.

---

## 4. 메시지 패턴 예시

MatMul+GELU 블록을 예로 들면:

1. `DMA_LOAD_TILE (ifm)` / `DMA_LOAD_TILE (wgt)`  
   - DRAM에서 SPM의 특정 bank/offset으로 tile 데이터를 이동.  
2. `TE_GEMM_TILE` / `VE_GELU_TILE`  
   - SPM bank들에서 데이터를 읽어 연산 수행, 결과를 SPM에 기록.  
3. `DMA_STORE_TILE (ofm)`  
   - SPM에서 DRAM으로 결과를 write-back.  

KV cache, attention, multi-head 등 LLM 시나리오는  
`docs/spec/timing/*.md` 및 `docs/spec/quantization/*.md`에서 bitwidth/traffic 모델과 함께 확장된다.

---

## 5. Cycle Loop와의 연계

Global cycle loop(`cycle_loop_design.md`)는 각 cycle마다:

- DMA/TE/VE/MemoryModel step 호출  
- DRAM/Bus/NoC/SPM 상태 업데이트  
- TraceEngine에 bandwidth/latency/conflict 이벤트 기록  

을 수행한다.

메모리/NoC 관련 trace 필드와 시각화 요구사항은  
`docs/spec/trace/trace_format_spec.md`, `visualization_requirements.md`에서 정의된다.

---

## 6. 향후 확장 아이디어

- Mobile LPDDR vs Server HBM 등 **프로파일별 메모리/NoC 구성 차이**를  
  표/다이어그램으로 비교하는 섹션 추가.  
- bank/port 구조 예시(간단한 숫자 예)와 함께  
  SPMAllocator/TilingPlanner가 어떤 제약을 보게 되는지 간단한 스토리로 설명.
