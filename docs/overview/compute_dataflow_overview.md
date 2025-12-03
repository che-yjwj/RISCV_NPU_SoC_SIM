# Compute Dataflow Overview
**Path:** `docs/overview/compute_dataflow_overview.md`  
**Version:** v1.0  
**Status:** Draft  
<!-- status: draft -->
**Owner:** System Architect  
**Last Updated:** 2025-12-03  

---

## 1. 목적 (Purpose)

이 문서는 `RISCV_NPU_SoC_SIM`에서 **연산(Compute) 중심 데이터 플로우**를  
한 번에 조망하기 위한 문서이다.

- ONNX → IR → TileGraph → Static Schedule → CMDQ → TE/VE 실행까지의  
  compute path에 집중한다.  
- 메모리/NoC/Trace/Process 등은 다른 overview 문서에서 보완한다.

더 광범위한 전체 데이터 플로우는 `docs/overview/dataflow_overview.md`를,  
메모리/NoC 관점은 `docs/overview/memory_noc_overview.md`를 참고한다.

---

## 2. 상위 Compute 파이프라인 (High-Level Compute Path)

```text
[ONNX Graph]
      │
      ▼
[IR Builder]
  - LayerIR / TensorIR
  - Quantization annotation (W/A/KV bits)
      │
      ▼
[Tiling Planner]
  - LayerIR → TileGraph
      │
      ▼
[Static Scheduler]
  - TileGraph → ScheduleDAG (TE/VE/DMA ops + deps)
      │
      ▼
[CMDQ Generator]
  - ScheduleDAG → CMDQ(JSON)
      │
      ▼
[NPU Simulator Core]
  - ControlFSM + TE/VE Engines
```

각 단계의 세부 내용은 다음 스펙/설계 문서에 정의된다.

- IR: `docs/spec/ir/npu_ir_spec.md`, `docs/spec/ir/tensor_metadata_spec.md`  
- Scheduler: `docs/design/tiling_planner_design.md`, `docs/design/static_scheduler_design.md`  
- CMDQ: `docs/spec/isa/cmdq_overview.md`, `docs/spec/isa/cmdq_format_spec.md`, `docs/design/cmdq_generator_design.md`  
- Simulator: `docs/design/npu_simulator_core_design.md`, `docs/design/te_engine_design.md`, `docs/design/ve_engine_design.md`

---

## 3. Compute 중심 시나리오 예시

### 3.1 MatMul + GELU 블록 (요약)

자세한 end-to-end 예시는 `dataflow_overview.md` 3.9 섹션에 있지만,  
여기서는 compute 관점에서만 간략히 정리한다.

1. **ONNX**: `MatMul(hidden, W)` → `GELU()`  
2. **IR**: `GEMM` 레이어 + `GELU` 레이어, 각 레이어에 qbits/shape/layout이 부여됨.  
3. **TileGraph**: GEMM 레이어가 M dimension 기준으로 여러 tile로 분해됨.  
4. **ScheduleDAG**:  
   - 각 tile에 대해 `DMA_LOAD_TILE` → `TE_GEMM_TILE` → `VE_GELU_TILE` → `DMA_STORE_TILE` 시퀀스 생성,  
   - 다수 tile은 multi-TE/VE에 분산되어 병렬 실행.  
5. **CMDQ**: ScheduleDAG 엔트리가 `DMA_LOAD_TILE` / `TE_GEMM_TILE` / `VE_GELU_TILE` / `DMA_STORE_TILE` opcode로 flatten.  
6. **Simulator**: ControlFSM가 CMDQ를 읽어 TE/VE 엔진에 issue, timing spec 기반으로 latency 계산.

보다 자세한 단계별 설명(특히 SPM 배치/Trace까지)은  
`docs/overview/dataflow_overview.md`의 3.9 섹션을 참고한다.

---

### 3.2 LLM Prefill/Decode (개요)

LLM 워크로드의 경우 compute dataflow가 두 단계로 나뉜다.

- **Prefill 단계**  
  - 긴 입력 시퀀스를 한 번에 처리하면서 KV cache를 DRAM/SPM에 채운다.  
  - MatMul/Attention/MLP 블록이 큰 시퀀스 타일로 실행되며,  
    KV cache tile append 연산이 연속적으로 발생한다.

- **Decode 단계**  
  - 한 토큰씩 또는 작은 윈도우 단위로 반복 실행한다.  
  - 각 step마다:
    - 과거 KV cache를 DRAM→SPM으로 DMA load  
    - Attention/MLP compute 실행  
    - 새로운 KV tile을 다시 DRAM으로 write-back  
  - CMDQ에서는 Prefill과 Decode를 서로 다른 구간(또는 phase tag)으로 구분해 표현할 수 있다.

LLM 특화 dataflow의 상세 그림과 KV cache 관련 예시는  
`docs/overview/dataflow_overview.md` 4장,  
그리고 IR/Quantization/Timing 스펙(`docs/spec/ir/*.md`, `docs/spec/quantization/*.md`, `docs/spec/timing/*.md`)에서 이어서 다룬다.

## 4. Compute vs 기타 관점 분리

이 문서는 **연산 경로**만 강조한다.  
다음 관점은 별도 문서를 통해 함께 읽는 것을 추천한다.

- **메모리/NoC 관점** → `docs/overview/memory_noc_overview.md`  
  - DRAM/Bus/NoC/SPM 구조, bank conflict, bandwidth, DMA 패턴 등  
- **프로세스/개발 플로우 관점** → `docs/overview/sdd_devflow_overview.md`  
  - Spec/Design/Test/코드/문서 개선 작업의 순서 및 규칙  

---

## 5. 향후 확장 아이디어

- Prefill/Decode 분리 및 KV cache를 포함한 **LLM 전용 compute dataflow**를  
  MatMul+GELU 예제와 유사한 형식으로 추가.  
- multi-TE/VE 구성에서 head parallelism/시퀀스 병렬화 전략을 별도 subsection으로 정리.
