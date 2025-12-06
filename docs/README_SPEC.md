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
│   ├── system_architecture_overview.md
│   ├── system_architecture.md
│   ├── dataflow_overview.md
│   ├── memory_noc_overview.md
│   ├── module_responsibilities.md
│   └── sdd_devflow_overview.md
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
│   ├── archive/
│   │   ├── review_by_chatgpt_v1.md
│   │   └── review_by_chatgpt_v2.md
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

- **system_architecture_overview.md** *(필수)* — 전체 아키텍처를 한 페이지에서 빠르게 파악하기 위한 요약본
- **system_architecture.md** *(필수)* — 전체 NPU + 컴파일러 + 시뮬레이터 아키텍처 상세 정의
- **dataflow_overview.md** *(권장)* — ONNX → IR → TileGraph → CMDQ → Simulator → Trace 전체 데이터 플로우 설명
- **memory_noc_overview.md** *(권장)* — DRAM/Bus/NoC/SPM 및 DMA 관점의 메모리/네트워크 구조 요약
- **module_responsibilities.md** *(권장)* — 각 모듈의 입력/출력 및 책임(SRP 기반)
- **sdd_devflow_overview.md** *(권장)* — Spec-Driven Development 기반 개발 흐름(Devflow) 상위 요약
    

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

## 4.1 Documentation Reading Guide (빠른 읽기 순서)

새로 레포를 읽는 기여자에게 추천하는 기본 순서는 다음과 같다.

1. **프로젝트 개요 및 디렉터리 구조**
   - `README.md` — 프로젝트 비전/범위/디렉터리 구조, 현재 구현 상태
   - `docs/README_SPEC.md` — 지금 보고 있는 문서, 전체 문서 인덱스/우선순위
2. **시스템 전체 그림**
   - `docs/overview/system_architecture.md` — 오프라인 컴파일러 + 시뮬레이터 아키텍처 개요
   - `docs/overview/dataflow_overview.md` — ONNX → IR → TileGraph → CMDQ → Simulator → Trace 데이터 흐름
   - `docs/overview/module_responsibilities.md` — 모듈 책임/입출력/경계 정의
3. **핵심 스펙 (IR / ISA / Timing / Quant / Trace)**
   - `docs/spec/ir/*.md` — 내부 IR 구조, 텐서 메타데이터, IR-level quantization 표현
   - `docs/spec/isa/*.md` — CMDQ 개념/포맷/opcode 정의
   - `docs/spec/timing/*.md` — DMA/TE/VE/SPM/Bus/NoC timing 모델
   - `docs/spec/quantization/*.md` — 전체 quantization 모델, bitwidth-memory 매핑, KV/mixed-precision 정책
   - `docs/spec/trace/*.md` — trace 포맷 및 시각화 스펙
4. **설계/테스트/프로세스**
   - `docs/design/*.md` — 컴파일러/시뮬레이터/Visualizer 설계 세부
   - `docs/test/*.md` — 테스트 전략/계획, golden trace 예시
   - `docs/process/*.md` — SDD 워크플로, 기여/리뷰 가이드, 네이밍/버전 규칙

이 순서를 따르면, **“무엇을 만들려는지 → 어떤 스펙인지 → 어떻게 설계/검증하는지”**를 자연스럽게 따라갈 수 있다.

## 4.2 Codex/Vibe Coding 및 문서 개선과의 연계

Codex 기반 Vibe Coding 또는 문서 개선 작업을 할 때는, 다음 세 문서를 함께 사용하는 것을 권장한다.

- 리뷰 스냅샷:  
  - `docs/process/archive/review_by_chatgpt_v1.md` (archive)  
  - `docs/process/archive/review_by_chatgpt_v2.md` (archive)
- 리뷰 요약/기준선:  
  - `docs/process/documentation_review_summary.md`
- 실행 가능한 체크리스트:  
  - `docs/process/doc_improvement_tasks.md`

추천 흐름은 다음과 같다.

1. 작업하려는 영역의 리뷰 스냅샷(v1/v2)을 확인해 개선 방향을 이해한다.  
2. `documentation_review_summary.md`에서 해당 계층(Overview/Spec/Design/Test 등)의 요약/권장사항을 읽는다.  
3. `doc_improvement_tasks.md`에서 관련 Task를 선택하거나 신규 Task를 추가한다.  
4. 이 인덱스 문서(`README_SPEC.md`)를 통해 필요한 Spec/Design/Test 문서 경로를 찾아 Codex 프롬프트에 포함한다.  
5. 작업 완료 후, Task 상태와 관련 문서의 Last Updated/Status를 갱신한다.

이 흐름을 통해, 이 파일은 단순 목차를 넘어  
**“무엇을 먼저 읽고, 무엇을 어떻게 고칠지”를 안내하는 중앙 허브** 역할을 하게 된다.

---

# 5. IR → CMDQ → Cycle Loop 파이프라인 맵

IR/ISA/CMDQ/Scheduler/Simulator를 하나의 흐름으로 보고 싶을 때는  
아래 표를 기준으로 각 단계의 스펙·설계 문서를 따라가면 된다.

| 단계 | 설명 | 주요 Spec 문서 | 주요 Design 문서 |
| --- | --- | --- | --- |
| 1. ONNX → IR | ONNX 그래프를 NPU IR(LayerIR/Tile-friendly 구조)로 변환 | `docs/spec/ir/npu_ir_spec.md`, `docs/spec/ir/tensor_metadata_spec.md`, `docs/spec/ir/quantization_ir_extension.md` | `docs/design/ir_builder_design.md` |
| 2. IR → TileGraph/MemoryPlan | LayerIR를 tile 단위 그래프로 분해하고 SPM(bank/offset) 계획 수립 | `docs/spec/ir/npu_ir_spec.md`, `docs/spec/timing/spm_model_spec.md` | `docs/design/tiling_planner_design.md`, `docs/design/spm_allocator_design.md` |
| 3. TileGraph → 정적 스케줄 | TileGraph + SPM + 엔진 구성을 이용해 tile-level 실행 순서/의존성(ScheduleDAG) 생성 | `docs/spec/isa/cmdq_overview.md` | `docs/design/static_scheduler_design.md` |
| 4. ScheduleDAG → CMDQ(JSON) | 스케줄 엔트리를 CMDQ 엔트리로 매핑하고 deps_before를 CMDQ index 기반으로 변환 | `docs/spec/isa/cmdq_overview.md`, `docs/spec/isa/cmdq_format_spec.md`, `docs/spec/isa/opcode_set_definition.md` | `docs/design/cmdq_generator_design.md` |
| 5. CMDQ → Cycle Loop 실행 | CMDQ를 ControlFSM가 fetch/issue하고, 엔진/타이밍 스펙에 따라 cycle loop에서 실행 | `docs/spec/isa/cmdq_overview.md`, `docs/spec/timing/*.md`, `docs/spec/trace/trace_format_spec.md` | `docs/design/control_fsm_design.md`, `docs/design/cycle_loop_design.md`, `docs/design/dma_engine_design.md`, `docs/design/te_engine_design.md`, `docs/design/ve_engine_design.md` |

- 전체적인 데이터/제어 흐름 개요는 `docs/overview/dataflow_overview.md`,  
  시스템 수준 아키텍처는 `docs/overview/system_architecture.md`를 함께 참고한다.  
- 향후에는 하나의 공통 예제(예: 단일 MatMul+GELU 또는 작은 LLaMA block)를 기준으로  
  각 단계의 artefact(ONNX → IR → TileGraph → ScheduleDAG → CMDQ → Trace)를  
  위 문서들에 걸쳐 예시로 추가하는 것을 목표로 한다.
