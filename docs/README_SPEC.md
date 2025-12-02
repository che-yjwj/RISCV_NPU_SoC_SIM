<!-- status: complete -->
# **NPU Simulator & Compiler — Spec Driven Development Master Index**
**Status:** Active  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

*(Repository Documentation Structure for SDD)*

본 문서는 전체 레포지토리에 필요한 **모든 스펙/설계/테스트 문서의 상위 목차**이다.

각 문서는 “코드보다 우선”이며, 모든 기능/확장은 이 문서 체계에 따라 진행해야 한다.

---

## 문서 우선순위 태그

| 태그 | 의미 | 비고 |
| --- | --- | --- |
| 필수 | 신규 기여자가 반드시 읽어야 하는 문서 | 아키텍처/핵심 스펙 |
| 권장 | 기능 구현 전에 읽으면 좋은 문서 | 모듈 책임, 타이밍, Trace 등 |
| 참고 | 세부 설계·프로세스 등 필요 시 확인 | 확장/심화 정보 |

---

## 대표 의존 관계 표

| 문서 | 우선순위 | 선행 문서 | 설명 |
| --- | --- | --- | --- |
| `docs/overview/system_architecture.md` | 필수 | README.md | 전체 아키텍처 기준선 |
| `docs/spec/ir/npu_ir_spec.md` | 필수 | overview/system_architecture.md, overview/dataflow_overview.md | 모든 컴파일러/시뮬레이터 단계가 참조 |
| `docs/spec/ir/quantization_ir_extension.md` | 권장 | spec/ir/npu_ir_spec.md | IR 확장 규칙이 IR 스펙을 상속 |
| `docs/spec/isa/cmdq_format_spec.md` | 필수 | spec/ir/npu_ir_spec.md, spec/isa/cmdq_overview.md | IR → CMDQ 변환 및 시뮬레이터가 의존 |
| `docs/design/static_scheduler_design.md` | 참고 | spec/ir/*.md, spec/isa/*.md | 스케줄러 설계는 IR/CMDQ 정의 후 검토 |
| `docs/test/test_plan.md` | 권장 | spec/design 전체 | 테스트 범위는 스펙/설계 정의를 기반으로 함 |

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

- **system_architecture.md** *(필수)* — 전체 NPU + 컴파일러 + 시뮬레이터 아키텍처 정의
- **dataflow_overview.md** *(권장)* — ONNX → IR → TileGraph → CMDQ → Simulator 경로 설명
- **module_responsibilities.md** *(권장)* — 각 모듈의 입력/출력 및 책임(SRP 기반)
    

---

## 2.2 Spec (핵심)

Spec Driven Development의 중심.

모든 기능은 이 spec 문서를 먼저 업데이트하고 코드 변경은 그 뒤에 진행한다.

### 2.2.1 IR 스펙

- **npu_ir_spec.md** *(필수)* — 내부 IR 구조, 노드, 텐서, 엣지 정의
- **quantization_ir_extension.md** *(권장)* — 레이어별 W/A/KV bitwidth 표현 방식
- **tensor_metadata_spec.md** *(권장)* — shape, dtype, qbits, layout 정보

### 2.2.2 ISA / CMDQ 스펙

- **cmdq_overview.md** *(필수)* — CMDQ 개념, execution model
- **cmdq_format_spec.md** *(필수)* — 엔트리 포맷(JSON/BIN), 스키마
- **opcode_set_definition.md** *(권장)* — DMA/TE/VE/BARRIER opcode 정의, 필드 설명

### 2.2.3 Timing Model 스펙

- **dma_timing_spec.md** *(권장)* — burst, bus_width, contention 공식
- **te_timing_spec.md** *(권장)* — GEMM/Conv latency 공식
- **ve_timing_spec.md** *(권장)* — SIMD/LN/Softmax latency
- **spm_model_spec.md** *(권장)* — multi-bank, port, conflict 모델
- **bus_and_noc_model.md** *(권장)* — DRAM/NoC 병목 모델링

### 2.2.4 Quantization 스펙

- **quantization_model_overview.md** *(권장)* — 전체 quant 모델
- **bitwidth_memory_mapping.md** *(권장)* — qbits → bytes → latency
- **kv_cache_quantization_spec.md** *(참고)* — KV 전용 bitwidth 스펙
- **mixed_precision_policy.md** *(참고)* — per-layer/per-tensor/per-group 확장 방법

### 2.2.5 Trace / Visualization 스펙

- **trace_format_spec.md** *(권장)* — 시뮬레이션 trace JSON 구조
- **gantt_timeline_spec.md** *(참고)* — TE/VE/DMA timeline 포맷
- **bandwidth_heatmap_spec.md** *(참고)* — BW 모니터링 포맷
- **visualization_requirements.md** *(참고)* — 시각적 요구사항 및 export 포맷

---

## 2.3 Design (TDD/TSD)

Spec 문서의 “설명된 내용을 실제로 어떻게 구현할지” 정의한다.

### Compiler Design

- **offline_compiler_design.md** *(참고)* — 전체 오프라인 컴파일러 파이프라인 흐름
- **ir_builder_design.md** *(참고)* — ONNX → NPU IR 변환 설계
- **tiling_planner_design.md** *(참고)* — 타일링 전략/정책 정의
- **spm_allocator_design.md** *(참고)* — SPM bank/offset 할당 알고리즘
- **static_scheduler_design.md** *(참고)* — tile-level 스케줄 DAG 생성 로직
- **cmdq_generator_design.md** *(참고)* — Schedule → CMDQ 변환 설계

### Simulator Design

- **npu_simulator_core_design.md** *(참고)* — Simulator 상위 모듈 구성
- **control_fsm_design.md** *(참고)* — CMDQ fetch/issue/complete FSM
- **dma_engine_design.md** *(참고)* — DMA 큐/상태머신 설계
- **te_engine_design.md** *(참고)* — Tensor Engine 파이프라인
- **ve_engine_design.md** *(참고)* — Vector Engine 파이프라인
- **cycle_loop_design.md** *(참고)* — Global cycle 기반 루프 구조

### Visualization

- **visualizer_design.md** *(참고)* — trace 기반 viewer 요구사항

---

## 2.4 Process 문서

**Spec-Driven Development 프로세스**를 지속적으로 지키기 위한 문서.

- **spec_driven_development_workflow.md** *(필수)*
    - 스펙 → 디자인 → 구현 → 테스트 → 리뷰의 순서를 정의
- **contribution_and_review_guide.md** *(권장)*
    - PR은 반드시 관련 Spec 문서 링크 포함
- **naming_convention.md** *(권장)*
    - IR 필드명, opcode명, class명 naming 규칙 통일
- **versioning_and_changelog_guide.md** *(참고)*
    - 문서/코드 버전 관리 규칙

---

## 2.5 Test 문서

스펙이 정확히 구현되었는지를 검증하는 문서들.

- **test_plan.md** *(권장)*
    
    전체 테스트 전략(기능, 성능, 회귀, 스트레스 테스트)
    
- **golden_trace_examples.md** *(참고)*
    
    대표 모델(MLP/Conv/Attention)에 대한 참조 trace
    
- **unit_test_spec.md** *(권장)*
    
    엔진/연산 단위 테스트 계획
    
- **integration_test_spec.md** *(권장)*
    
    온전한 End-to-End test
    
- **performance_validation_protocol.md** *(참고)*
    
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
