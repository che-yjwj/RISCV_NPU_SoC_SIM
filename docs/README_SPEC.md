<!-- status: complete -->
# **NPU Simulator & Compiler — Spec Driven Development Master Index**

*(Repository Documentation Structure for SDD)*

본 문서는 전체 레포지토리에 필요한 **모든 스펙/설계/테스트 문서의 상위 목차**이다.

각 문서는 “코드보다 우선”이며, 모든 기능/확장은 이 문서 체계에 따라 진행해야 한다.

---

# 1. 레포지토리 문서 디렉터리 구조

```
docs/
│
├── overview/
│   ├── system_architecture.md
│   ├── dataflow_overview.md
│   └── module_responsibilities.md
│
├── spec/
│   ├── ir/
│   │   ├── npu_ir_spec.md
│   │   ├── quantization_ir_extension.md
│   │   └── tensor_metadata_spec.md
│   │
│   ├── isa/
│   │   ├── cmdq_overview.md
│   │   ├── cmdq_format_spec.md
│   │   └── opcode_set_definition.md
│   │
│   ├── timing/
│   │   ├── dma_timing_spec.md
│   │   ├── te_timing_spec.md
│   │   ├── ve_timing_spec.md
│   │   ├── spm_model_spec.md
│   │   └── bus_and_noc_model.md
│   │
│   ├── quantization/
│   │   ├── quantization_model_overview.md
│   │   ├── bitwidth_memory_mapping.md
│   │   ├── kv_cache_quantization_spec.md
│   │   └── mixed_precision_policy.md
│   │
│   └── trace/
│       ├── trace_format_spec.md
│       ├── gantt_timeline_spec.md
│       ├── bandwidth_heatmap_spec.md
│       └── visualization_requirements.md
│
├── design/
│   ├── offline_compiler_design.md
│   ├── ir_builder_design.md
│   ├── tiling_planner_design.md
│   ├── spm_allocator_design.md
│   ├── static_scheduler_design.md
│   ├── cmdq_generator_design.md
│   ├── npu_simulator_core_design.md
│   ├── control_fsm_design.md
│   ├── dma_engine_design.md
│   ├── te_engine_design.md
│   ├── ve_engine_design.md
│   ├── cycle_loop_design.md
│   └── visualizer_design.md
│
├── process/
│   ├── spec_driven_development_workflow.md
│   ├── contribution_and_review_guide.md
│   ├── naming_convention.md
│   └── versioning_and_changelog_guide.md
│
└── test/
    ├── test_plan.md
    ├── golden_trace_examples.md
    ├── unit_test_spec.md
    ├── integration_test_spec.md
    └── performance_validation_protocol.md

```

---

# 2. 상위 문서 설명 (TOC)

## 2.1 Overview

NPU 시스템의 큰 그림, 데이터 흐름, 책임 분할 문서들

- **system_architecture.md**
    
    전체 NPU + 컴파일러 + 시뮬레이터 아키텍처 정의
    
- **dataflow_overview.md**
    
    ONNX → IR → TileGraph → CMDQ → Simulator 경로 설명
    
- **module_responsibilities.md**
    
    각 모듈의 입력/출력 및 책임(Single Responsibility Principle 기반)
    

---

## 2.2 Spec (핵심)

Spec Driven Development의 중심.

모든 기능은 이 spec 문서를 먼저 업데이트하고 코드 변경은 그 뒤에 진행한다.

### 2.2.1 IR 스펙

- **npu_ir_spec.md** — 내부 IR 구조, 노드, 텐서, 엣지 정의
- **quantization_ir_extension.md** — 레이어별 W/A/KV bitwidth 표현 방식
- **tensor_metadata_spec.md** — shape, dtype, qbits, layout 정보

### 2.2.2 ISA / CMDQ 스펙

- **cmdq_overview.md** — CMDQ 개념, execution model
- **cmdq_format_spec.md** — 엔트리 포맷(JSON/BIN), 스키마
- **opcode_set_definition.md** — DMA/TE/VE/BARRIER opcode 정의, 필드 설명

### 2.2.3 Timing Model 스펙

- **dma_timing_spec.md** — burst, bus_width, contention 공식
- **te_timing_spec.md** — GEMM/Conv latency 공식
- **ve_timing_spec.md** — SIMD/LN/Softmax latency
- **spm_model_spec.md** — multi-bank, port, conflict 모델
- **bus_and_noc_model.md** — DRAM/NoC 병목 모델링

### 2.2.4 Quantization 스펙

- **quantization_model_overview.md** — 전체 quant 모델
- **bitwidth_memory_mapping.md** — qbits → bytes → latency
- **kv_cache_quantization_spec.md** — KV 전용 bitwidth 스펙
- **mixed_precision_policy.md** — per-layer/per-tensor/per-group 확장 방법

### 2.2.5 Trace / Visualization 스펙

- **trace_format_spec.md** — 시뮬레이션 trace JSON 구조
- **gantt_timeline_spec.md** — TE/VE/DMA timeline 포맷
- **bandwidth_heatmap_spec.md** — BW 모니터링 포맷
- **visualization_requirements.md** — 시각적 요구사항 및 export 포맷

---

## 2.3 Design (TDD/TSD)

Spec 문서의 “설명된 내용을 실제로 어떻게 구현할지” 정의한다.

### Compiler Design

- offline_compiler_design.md
- ir_builder_design.md
- tiling_planner_design.md
- spm_allocator_design.md
- static_scheduler_design.md
- cmdq_generator_design.md

### Simulator Design

- npu_simulator_core_design.md
- control_fsm_design.md
- dma_engine_design.md
- te_engine_design.md
- ve_engine_design.md
- cycle_loop_design.md

### Visualization

- visualizer_design.md

---

## 2.4 Process 문서

**Spec-Driven Development 프로세스**를 지속적으로 지키기 위한 문서.

- **spec_driven_development_workflow.md**
    - 스펙 → 디자인 → 구현 → 테스트 → 리뷰의 순서를 정의
- **contribution_and_review_guide.md**
    - PR은 반드시 관련 Spec 문서 링크 포함
- **naming_convention.md**
    - IR 필드명, opcode명, class명 naming 규칙 통일
- **versioning_and_changelog_guide.md**
    - 문서/코드 버전 관리 규칙

---

## 2.5 Test 문서

스펙이 정확히 구현되었는지를 검증하는 문서들.

- **test_plan.md**
    
    전체 테스트 전략(기능, 성능, 회귀, 스트레스 테스트)
    
- **golden_trace_examples.md**
    
    대표 모델(MLP/Conv/Attention)에 대한 참조 trace
    
- **unit_test_spec.md**
    
    엔진/연산 단위 테스트 계획
    
- **integration_test_spec.md**
    
    온전한 End-to-End test
    
- **performance_validation_protocol.md**
    
    latency 예측 정확도 검증 방법
    

---

# 3. Spec-Driven Development를 위한 실행 규칙

1. **코드보다 문서가 먼저**
    - 기능 추가 시:
        - ① Spec 업데이트 → ② Design 업데이트 → ③ 코드 구현 → ④ Test 업데이트
2. **명시적 인터페이스 기반 개발**
    - CMDQ/IR/Trace는 JSON Schema 또는 테이블로 고정
3. **변경 관리(Change Control)**
    - 모든 스펙 문서는 버전 관리
    - 변경 시 PR에 “이 스펙의 어떤 부분이 변경되었는지” 명시
4. **Golden Trace 기반 회귀 검증**
5. **문서/코드/비주얼이 항상 동기화된 상태 유지**

---

# 4. 이 파일을 어떻게 사용하면 좋은가?

- 이 문서(`README_SPEC.md`)는 **레포 문서의 최상위 목차**로 사용
- 모든 기여자는 기능 추가 시 이 문서의 spec 항목을 먼저 읽어야 함
- 스펙을 기반으로 실제 구현이 이루어지므로
    
    “설계-문서-코드-테스트”가 **완전히 일치**하는 구조가 된다
