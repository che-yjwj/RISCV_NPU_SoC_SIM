# Milestone Plan v1 — Skeleton-First SDD Implementation Roadmap
Status: Draft v1  
Owner: TBD  
Last Updated: 2025-12-02  

---

## 1. 목적 (Purpose)

본 문서는 `RISCV_NPU_SoC_SIM` 레포지토리(현재 기준: 문서 중심 코드베이스, `docs/` 및 `tools/doc_status.py` 존재)를 기반으로,  
Spec-Driven Development(SDD) 원칙에 따라 실제 구현을 진행하기 위한 단계별 마일스톤 계획을 정의한다.

현재 레포는 다음과 같은 특징을 가진다.

- 상위 개요: `README.md`, `docs/README_SPEC.md`
- Spec: `docs/spec/**` (IR, ISA/CMDQ, Timing, Quantization, Trace 등)
- Design: `docs/design/**` (Simulator Core, Engines, Compiler Pass, Visualizer 등)
- Process: `docs/process/**` (SDD 워크플로, 네이밍 규칙, 버저닝 등)
- Test: `docs/test/**`
- 참고 아카이브: `docs/references/**` (본 마일스톤에서는 무시)

이 문서는 위 문서 스택을 전제로, 실제 소스 코드 구조를 정의하고, Phase별로 구현 범위와 완료 기준을 명시한다.

---

## 2. 공통 원칙

1. 문서 → 설계 → 코드 순서의 SDD 플로우를 유지한다.  
2. 디렉터리/모듈/클래스 이름은 가급적 `docs/spec`, `docs/design`에 정의된 명칭을 따른다.  
3. 각 Phase는 가능한 한 세로로 얇은 End-to-End 경로를 먼저 완성하고, 이후 가로 방향으로 기능을 확장한다.  
4. `docs/references/**`에 있는 이전 세대 문서들은 히스토리로만 사용하고, 본 계획의 기준에서는 제외한다.

---

## 3. Phase 0 — 프로젝트 코드 스켈레톤 구축

### 3.1 Goal

- 문서 구조와 1:1로 매핑되는 Python 패키지 스켈레톤을 생성한다.
- 이 단계에서는 실제 기능 구현 없이, 타입/모듈의 “껍데기”만 정의한다.

### 3.2 Scope

- `src/` 또는 최상위 패키지 디렉터리(예: `riscv_npu_sim/`) 생성
- compiler / simulator / common / cli / tests 디렉터리 구축
- IR, CMDQ, Timing, Trace 등 핵심 도메인 모델 타입의 dataclass 정의
- pytest 기반 테스트 인프라 기본 구성

### 3.3 제안 디렉터리 구조

```text
riscv_npu_sim/
  __init__.py

  compiler/
    __init__.py
    ir/
      __init__.py
      core_types.py          # IrNode, TensorMeta, QuantMeta, IrGraph 등
    passes/
      __init__.py
      ir_builder.py
      tiling_planner.py
      spm_allocator.py
      static_scheduler.py
      cmdq_generator.py

  simulator/
    __init__.py
    core/
      __init__.py
      npu_simulator.py       # NpuSimulator, cycle loop
      control_fsm.py         # ControlFSM
    engines/
      __init__.py
      te_engine.py
      ve_engine.py
      dma_engine.py
    timing/
      __init__.py
      te_timing.py
      ve_timing.py
      dma_timing.py
      spm_timing.py
      bus_noc_timing.py
    memory/
      __init__.py
      spm_model.py
      dram_model.py
    trace/
      __init__.py
      trace_types.py
      trace_writer.py

  common/
    __init__.py
    config.py
    enums.py
    logging.py

  cli/
    __init__.py
    main.py

tests/
  unit/
  integration/
  golden/

tools/
  doc_status.py  # 기존 파일 유지
```

### 3.4 Tasks (Phase 0)

- [ ] (P0-SKEL-001) `riscv_npu_sim/` 패키지 디렉터리 생성
- [ ] (P0-SKEL-002) 위 구조에 해당하는 `__init__.py` 및 빈 모듈 파일 생성
- [ ] (P0-IR-CORE-001) `compiler/ir/core_types.py`에 IR / Tensor / Quant / CMDQ / Timing / Trace dataclass 골격 정의
  - 필드 이름 및 기본 구조는 다음 문서에 맞춤
    - `docs/spec/ir/npu_ir_spec.md`
    - `docs/spec/ir/tensor_metadata_spec.md`
    - `docs/spec/ir/quantization_ir_extension.md`
    - `docs/spec/isa/cmdq_format_spec.md`
    - `docs/spec/timing/*.md`
    - `docs/spec/trace/trace_format_spec.md`
- [ ] (P0-BLD-001) `pyproject.toml` 또는 `setup.cfg` 등 빌드 설정(선택)
- [ ] (P0-T-INFRA-001) `pytest` 설정 및 최소 sanity test 추가

### 3.5 Done Criteria

- `python -m pip install -e .` 또는 유사 방식으로 로컬 설치 가능
- `python -c "import riscv_npu_sim"` 수행 시 ImportError 없이 통과
- `pytest` 실행 시, Phase 0에서 정의한 최소 테스트가 통과
- 문서에서 언급되는 주요 엔티티 이름이 모두 코드 스켈레톤에 존재

---

## 4. Phase 1 — MatMul-only End-to-End 파이프라인 스켈레톤

### 4.1 Goal

아주 단순한 MatMul-only ONNX 모델에 대해:

- ONNX → IR → (단순) Tiling → (단순) SPMAlloc → (순차) StaticSchedule → CMDQ → Simulator → Trace

까지 한 번 관통하는 End-to-End 경로를 만든다.  
이 단계에서는 정확한 타이밍/성능이 아니라, “데이터가 흐르는 파이프라인”이 핵심이다.

### 4.2 Scope

- 지원 연산: MatMul 1종
- 타일링: 실제 분할 없이 “단일 타일” 전략
- SPM Alloc: bank=0, offset=0 등 단순 정책
- 스케줄링: CMDQ 순차 실행
- Simulator: TE 엔진 단일, 간단한 latency 계산
- Trace: MatMul 실행 구간만 기록

### 4.3 Tasks (Compiler)

- [ ] (P1-C-IRB-001) IrBuilderPass: ONNX MatMul → IR 변환
  - 위치: `compiler/passes/ir_builder.py`
  - 역할: ONNX MatMul 노드를 IRGraph의 `IrNode(op_type=MatMul)`로 변환
  - 참조 문서:
    - `docs/design/ir_builder_design.md`
    - `docs/spec/ir/npu_ir_spec.md`
- [ ] (P1-C-TLP-001) TilingPlannerPass: 단일 타일 버전
  - 위치: `compiler/passes/tiling_planner.py`
  - 역할: 전체 MatMul을 하나의 타일로 모델링
  - 참조 문서:
    - `docs/design/tiling_planner_design.md`
- [ ] (P1-C-SPM-001) SpmAllocatorPass: simple-sequential SPM 배치
  - 위치: `compiler/passes/spm_allocator.py`
  - 역할: 모든 텐서를 SPM bank=0, offset 순차 증가 방식으로 배치
  - 참조 문서:
    - `docs/design/spm_allocator_design.md`
- [ ] (P1-C-SCH-001) StaticSchedulerPass: sequential schedule 생성
  - 위치: `compiler/passes/static_scheduler.py`
  - 역할: 타일 그래프 노드를 순차 실행하는 스케줄 생성 (deps 단순화)
  - 참조 문서:
    - `docs/design/static_scheduler_design.md`
- [ ] (P1-C-CMDQ-001) CmdqGeneratorPass: TE MatMul CMDQ 생성
  - 위치: `compiler/passes/cmdq_generator.py`
  - 역할: 스케줄 결과를 TE용 MatMul CMDQ 엔트리 리스트로 변환
  - 참조 문서:
    - `docs/spec/isa/cmdq_overview.md`
    - `docs/spec/isa/cmdq_format_spec.md`
    - `docs/design/cmdq_generator_design.md`

### 4.4 Tasks (Simulator)

- [ ] (P1-S-SIM-001) NpuSimulator: global cycle loop 스켈레톤
  - 위치: `simulator/core/npu_simulator.py`
  - 역할: global cycle loop 및 각 엔진/ControlFSM 호출
  - 참조 문서:
    - `docs/design/npu_simulator_core_design.md`
    - `docs/design/cycle_loop_design.md`
- [ ] (P1-S-CTRL-001) ControlFSM: sequential issue
  - 위치: `simulator/core/control_fsm.py`
  - 역할: CMDQ를 순차로 TE 엔진에 issue
  - 참조 문서:
    - `docs/design/control_fsm_design.md`
- [ ] (P1-S-TE-001) TeEngine: naive MAC-based latency 모델
  - 위치: `simulator/engines/te_engine.py`
  - 역할: MatMul CMDQ를 받아 단순 latency 후 완료 처리
- [ ] (P1-S-TRC-001) TraceCollector: MatMul 실행 구간 기록
  - 위치: `simulator/trace/trace_writer.py` 또는 `trace_types.py`
  - 역할: MatMul 실행 구간(start_cycle, end_cycle)과 CMD ID 기록

### 4.5 Tasks (Test)

- [ ] (P1-T-INTEG-001) 통합 테스트: `tests/integration/test_single_matmul_pipeline.py`
  - ONNX MatMul 1개 모델을 사용
  - CMDQ 생성, Simulator 실행, Trace JSON 생성까지 검증

### 4.6 Done Criteria

- MatMul-only ONNX 모델에 대해:
  - CMDQ 생성 성공
  - Simulator가 cycle loop를 돌고 정상 종료
  - Trace 파일이 정의된 포맷(`docs/spec/trace/trace_format_spec.md`)의 최소 subset을 만족하며 생성

---

## 5. Phase 2 — Timing/Memory/엔진 모델 현실화

### 5.1 Goal

- TE/VE/DMA/SPM/DRAM 엔진이 문서에 정의된 기본 타이밍/자원경합 모델을 갖추도록 구현한다.
- MatMul + 간단한 elementwise(Add/GELU 등)를 대상으로 “엔진 overlap”과 “BW/latency 영향”을 관찰할 수 있는 수준을 목표로 한다.

### 5.2 Scope

- Timing:
  - TE/VE throughput, pipeline latency
  - DMA bandwidth, DRAM base latency, burst 개념
  - SPM access latency, bank conflict 모델
- Engine:
  - TE/VE/DMA Engine의 busy 상태 및 `can_accept` 정책
- ControlFSM:
  - deps 처리, 자원 상태를 반영한 issue 정책
- Trace:
  - 엔진별 시작/종료 cycle, BW 사용량, 타일/텐서 메타데이터

### 5.3 Tasks

- [ ] TE timing 함수 구현 (`simulator/timing/te_timing.py`)
  - `docs/spec/timing/te_timing_spec.md` 참조
- [ ] VE timing 함수 구현 (`simulator/timing/ve_timing.py`)
  - `docs/spec/timing/ve_timing_spec.md` 참조
- [ ] DMA timing 함수 구현 (`simulator/timing/dma_timing.py`)
  - `docs/spec/timing/dma_timing_spec.md` 참조
- [ ] SPM timing/bank 모델 구현 (`simulator/memory/spm_model.py`)
  - `docs/spec/timing/spm_model_spec.md` 참조
- [ ] Bus/NoC 간단 모델 구현 (`simulator/timing/bus_noc_timing.py`)
  - `docs/spec/timing/bus_and_noc_model.md` 참조
- [ ] Engine 구현 확장 (`te_engine.py`, `ve_engine.py`, `dma_engine.py`)
  - `can_accept`, `issue`, `step` 인터페이스 정교화
- [ ] ControlFSM 확장 (`control_fsm.py`)
  - deps_before, 엔진 busy 상태 등을 고려한 스케줄링 로직 구현
- [ ] Trace 확장 (`trace_types.py`, `trace_writer.py`)
  - Gantt timeline, BW heatmap에서 요구하는 필드까지 포함
  - `docs/spec/trace/gantt_timeline_spec.md`, `bandwidth_heatmap_spec.md` 참조
- [ ] Unit/Integration 테스트 강화 (timing 예제 기반)

### 5.4 Done Criteria

- MatMul + Add 그래프에 대해:
  - TE/VE/DMA timeline 및 DRAM BW 사용 패턴이 spec에서 기대한 방향과 일치
  - Trace 기반 Gantt/BW 뷰어를 연결했을 때 의미 있는 결과가 나옴

---

## 6. Phase 3 — IR/Tiling/Scheduling 정교화 및 Conv/Attention 추가

### 6.1 Goal

- Conv, Attention 등 핵심 연산을 IR/타일링/스케줄링/CMDQ/엔진 레벨까지 end-to-end로 지원한다.
- 타일링/스케줄링 정책 변경이 시뮬레이션 결과(타임라인, BW, SPM 사용량)에 반영되는 구조를 확보한다.

### 6.2 Scope

- IR op 확장(MatMul → Conv, Attention)
- TilingPlanner 정책 확장(2D, 시퀀스/헤드 축 분할 등)
- StaticScheduler 정책 정교화(DMA prefetch, TE/VE overlap, 우선순위)
- SPMAllocator weight/activation/KV 파티셔닝 정책 반영

### 6.3 Tasks (요약)

- [ ] Conv IR 지원 (IrBuilderPass)
- [ ] Attention IR 지원 (Q/K/V, softmax, output)
- [ ] Conv/Attention 타일링 규칙 구현 (TilingPlannerPass)
- [ ] SPMAllocator에서 KV/weight/activation의 서로 다른 배치 규칙 구현
- [ ] StaticScheduler의 정책 파라미터(config)화 및 구현
- [ ] Conv/Attention용 CMDQ opcode 및 args 정의 (`opcode_set_definition.md` 연계)
- [ ] Conv/Attention용 TE kernel/latency 모델 구현

### 6.4 Done Criteria

- Conv-only, Attention-only, MatMul+GELU+Attention 조합 그래프에 대해:
  - CMDQ와 Trace가 원하는 수준으로 생성 및 해석 가능

---

## 7. Phase 4 — Quantization + LLM Prefill/Decode + KV Cache

### 7.1 Goal

- Quantization, KV cache, LLM prefill/decoder 모드를 실제 코드에 반영한다.
- 모바일 NPU LLM inference 용도로 의미 있는 분석이 가능한 수준까지 끌어올린다.

### 7.2 Scope

- QuantMeta 및 bitwidth 기반 메모리/대역폭 모델 구현
- KV cache quant 및 배치 정책 구현
- Prefill/Decode phase 분리 및 CMDQ tagging
- Trace에 phase 정보 및 KV access 패턴 반영

(세부 Task는 기존 초안과 동일한 구조이되, 실제 구현 시 `docs/spec/quantization/*.md`, `docs/spec/workload(추가 예정)`와 연계)

---

## 8. Phase 5 — DSE / Multi-scenario / CLI & Report

### 8.1 Goal

- 이 시뮬레이터를 NPU 설계 공간 탐색 및 실험 플랫폼으로 승격한다.
- 다양한 config/profiles/시나리오를 정의하고, CLI/리포트/뷰어까지 갖춘 end-to-end 툴체인으로 완성한다.

(세부 내용은 기존 초안과 유사하며, DSE 엔진, Scenario YAML, CLI(`sim run`, `sim dse`), summary report, viewer 연동 등으로 구성)

---

## 9. 요약

- 현재 레포는 문서 스택이 잘 정리된 “pre-code” 상태이다.
- Phase 0에서 코드 스켈레톤을 만들고,
- Phase 1에서 MatMul-only 세로 파이프라인을 관통시키며,
- Phase 2~5에서 timing/ops/LLM/DSE를 단계적으로 확장한다.

이 Milestone Plan은 `docs/process/milestone_plan.md`로 추가하여,  
향후 모든 구현/PR/테스트 계획의 기준 문서로 사용한다.
