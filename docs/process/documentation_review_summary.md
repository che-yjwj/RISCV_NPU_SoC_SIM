# Documentation Review Summary
**Path:** `docs/process/documentation_review_summary.md`  
**Status:** Reference  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---
본 문서는 `RISCV_NPU_SoC_SIM` 레포지토리의 문서 구조를 기반으로,  
`docs/references/`를 제외한 주요 문서들에 대한 리뷰 내용을 요약한 참조용 문서이다.  
각 섹션은 **역할 요약 → 강점 → 개선 제안** 순으로 구성되어 있으며,  
이하의 본문은 `review_by_chatgpt_v1.md`(기존 `review_by_chatgpt.md`) 최초 버전에서 작성된 내용을 그대로 보존한다.  
실제 개선 작업과 진행 상황은 `docs/process/doc_improvement_tasks.md`에서 추적한다.

# RISCV_NPU_SoC_SIM 문서 리뷰 요약

본 문서는 `RISCV_NPU_SoC_SIM` 레포지토리의 문서 구조를 기반으로, `docs/references/`를 제외한 주요 문서들에 대한 리뷰를 정리한 것이다.  
각 섹션은 **역할 요약 → 강점 → 개선 제안** 순으로 구성하였다.

---

## 0. 레포 루트

### `README.md`

**역할 요약**  
프로젝트 비전·범위·디렉터리 구조를 한 번에 보여주는 상위 소개 문서.

**강점**  
- “정적 스케줄 기반 NPU 시뮬레이터 & 오프라인 컴파일러”라는 목적이 매우 명확함.
- 컴파일러/시뮬레이터/트레이스·테스트까지 한 번에 조망 가능해, 새로운 사람이 들어와도 전체 구조를 빠르게 이해할 수 있음.
- 디렉터리 구조 설명이 구체적(compiler/simulator/common/tests/tools 등)이라 실제 코드 구조와 매핑하기 좋음.

**개선 제안**  
- “현재 구현 상태(implemented / partially implemented / planned)”를 간단한 표나 섹션으로 추가하면 실무 프로젝트 README처럼 더 좋아짐.
- “추천 읽기 순서”에 `docs/README_SPEC.md` 이하 문서들을 번호로 명시하면 문서 네트워크가 더 잘 드러남.
- 예상 타깃(모바일 NPU / 서버 NPU / 연구용 시뮬레이터 등)을 1–2줄로 다시 못 박으면 scope 논의에 도움이 됨.

---

## 1. 상위 Spec 인덱스 및 Overview 계층

### `docs/README_SPEC.md`

**역할 요약**  
`docs/` 아래 전체 문서들의 카탈로그이자, SDD(Spec-Driven Development) 기반의 읽기 순서를 정의하는 상위 인덱스 문서.

**강점**  
- overview / spec / design / process / test로 계층이 잘 나뉘어 있고, 각 폴더의 역할이 명확함.
- “먼저 읽어야 할 문서 → 이후 상세 스펙” 순서를 제안하는 구조가 SDD 워크플로우와 잘 맞음.

**개선 제안 (v1+v2 통합)**  
- 각 문서에 “필수 / 권장 / 참고” 레벨 태그를 달고, 우선 읽기 순서를 보다 명시적으로 표현할 것.  
- `docs/overview/*` 문서들과 연결되는 navigation 섹션을 보강하고, 전체 시스템 아키텍처 및 onnx→ir→compile→sim 파이프라인을 한 번에 보여주는 다이어그램/표를 추가할 것.  
- 주요 문서 간 의존 관계를 간단한 표(예: IR Spec ← Quantization IR Extension ← Tiling Planner Design…)로 정리할 것.

### `docs/overview/system_architecture.md`, `dataflow_overview.md`, `module_responsibilities.md`

**역할 요약**  
오프라인 컴파일러 + NPU 시뮬레이터 전체 아키텍처, 데이터 플로우, 모듈 책임을 설명하는 상위 overview 문서들.

**강점**  
- IRBuilder, Tiling, StaticScheduler, CmdqGenerator, Simulator Core, TraceEngine 등 주요 블록이 모두 등장해 big picture를 이해하기 좋음.
- ONNX → IR → TileGraph → CMDQ → Simulator로 이어지는 데이터 플로우와, 각 모듈의 책임 범위/하지 말아야 할 일을 구분하려는 시도가 있음.

**개선 제안 (v1+v2 통합)**  
- RISC-V SoC 관점(CPU/AXI/인터럽트/메모리 계층)에서의 연결을 블록 다이어그램(텍스트 기반이라도)으로 명시해 SoC 독자도 이해하기 쉽게 할 것.  
- 대표 예시(예: 단일 MatMul+GELU 또는 LLaMA block)를 기준으로 ONNX → IR → TileGraph → CMDQ → Trace까지 한 줄씩 이어지는 end-to-end 예제를 추가할 것.  
- v2 리뷰에서 제안된 신규/보완 문서(예: `system_architecture_overview.md`, `compute_dataflow_overview.md`, `memory_noc_overview.md`, `sdd_devflow_overview.md`)를 실제 구조에 맞게 설계·추가해, overview 계층만 읽어도 전체 그림과 개발 플로우를 파악할 수 있게 할 것.

---

## 2. Spec / IR / ISA / Timing / Quantization 계층

### IR 스펙 (`docs/spec/ir/*.md`)

**역할 요약**  
내부 NPU IR의 전체 구조, 노드/텐서 스키마, 타일 변환 및 메타데이터 표현 규칙을 정의하는 핵심 스펙 문서들.

**강점**  
- “IR이 단일 source of truth”라는 방향성이 명시적이며, LLM 친화 요소(KV cache, attention op, mixed precision 등)를 고려한 설계 철학이 드러남.
- 텐서 메타데이터(레이아웃/stride/메모리 위치 등)를 별도 스펙으로 분리해 SPM/Timing 등 다른 모듈과 공유할 수 있는 기반이 있음.

**개선 제안 (v1+v2 통합)**  
- IR 노드 타입별(예: MatMul, Conv, Attention, Load/Store 등) 필드/속성/제약조건을 표로 정리해 구현자가 빠르게 참조할 수 있게 할 것.  
- IR pass pipeline을 명시적으로 정의: `ONNX → Canonicalize → ShapeInference → Tiling → MemoryPlan → Scheduling → CMDQ → ISA Lowering` 등의 형태로 단계와 산출물을 명확히 할 것.  
- IR 버전 관리 정책(필드 추가/제거 시 호환성, IR version tag 등)을 짧게라도 명시하고, SPMAllocator/Timing/Trace에서 공유해야 하는 메타데이터 필드(SPM bank, alignment 등)를 align할 것.

### ISA / CMDQ 스펙 (`docs/spec/isa/*.md`)

**역할 요약**  
CMDQ 개념과 포맷, opcode 집합을 정의해 IR→CMDQ→Simulator 실행 파이프라인을 formal하게 연결하는 스펙.

**강점**  
- CMDQ를 “정적 명령 스트림”으로 규정하고, Offline Compiler / Simulator / Trace 관점에서의 역할과 시야를 분리해 설명함.
- `cmdq_format_spec.md`에서 deps, engine_type, tiling 관련 필드를 중심으로 JSON 포맷을 비교적 구조적으로 다룸.

**개선 제안 (v1+v2 통합)**  
- 소규모 예제 CMDQ(JSON)를 하나 정의하고, 각 필드에 대한 주석을 달아 Golden CMDQ 기준으로 사용할 것.  
- 필드별 “필수/옵션/예약(reserved)” 구분을 표로 정의해 확장성을 높이고, IR op ↔ CMDQ opcode 매핑 표를 추가해 IR-to-CMDQ 단계 설계에 도움을 줄 것.  
- Prefill/Decode 워크로드에서 CMDQ 스트림을 어떻게 분리/공유할지(멀티 스트림 또는 단일 스트림 + phase tag 등)를 high-level 정책으로 적어 둘 것.

### Timing / Quantization / Trace 스펙

**역할 요약**  
DMA/TE/VE/SPM/Bus/NoC 타이밍 모델, 양자화 정책, Trace 포맷 및 시각화 요구사항을 정의하는 보조 스펙 계층.

**강점**  
- DMA/TE/VE timing에서 bus width, burst, bank conflict, multi-channel contention 등 실제 NPU에서 중요한 요소를 고려 대상으로 두고 있음.
- Quantization 스펙에서 KV cache, mixed-precision, bitwidth-memory mapping을 분리해 정의해 LLM 특화 시나리오를 다룰 기반이 마련됨.
- Trace/Visualization 스펙에서 Gantt-style timeline, bandwidth heatmap 등 시각화 요구사항을 명시해 추후 툴 체인과의 연동 가능성을 열어둠.

**개선 제안 (v1+v2 통합)**  
- Timing 스펙에는 실제 시뮬레이션에서 사용할 config 예시(JSON)를 추가하고, LPDDR/HBM 등 여러 프로파일을 지원할 계획이라면 profile 개념을 간단히 언급할 것.  
- Quantization 스펙에서는 IR/ISA와의 연결 지점을 “IR 필드 매핑표 + 예제 IR 스니펫(JSON)” 형태로 보강하고, KV cache quant vs 일반 activation quant 차이를 비교표로 정리할 것.  
- Trace/Visualization 스펙에서는 최소 1개의 축약 trace 예제를 포함하고, 시각화에 필요한 필드를 표(필드/타입/필수 여부) 형태로 명시하며, Prefill/Decode 구분 규칙(색/태그 등)을 high-level로 정의할 것.

---

## 3. Design / Simulator / Compiler 계층

**역할 요약**  
시뮬레이터 코어, cycle loop, Control FSM, DMA/TE/VE/SPMAllocator/StaticScheduler, Offline Compiler, Visualizer 등 주요 모듈의 구조와 알고리즘을 정의하는 설계 문서 계층.

**공통 강점**  
- Path / Status / Owner / Last Updated 헤더가 통일되어 있어 SDD/리뷰 워크플로우에 적합함.  
- “목적 → 책임 → 입출력 → 내부 구조 → 알고리즘” 순서로 구성된 문서가 많아 실제 구현자가 바로 코드로 옮기기 좋음.  
- 관련 Spec 문서를 상단에 링크하는 패턴이 잘 잡혀 있어 문서 간 네비게이션이 자연스러움.

**공통 개선 제안 (v1+v2 통합)**  
- 대부분의 design 문서에 대해 Owner 지정, Last Updated 갱신, 구현 상태 플래그(미구현/부분 구현/완료)를 추가해 roadmap을 명확히 할 것.  
- Simulator Core / Cycle Loop / Control FSM / DMA/TE/VE 등에 대해 텍스트 설명뿐 아니라 간단한 다이어그램(상태도, 파이프라인 스케치, 시퀀스 다이어그램)을 추가해 구조를 시각적으로 이해하기 쉽게 할 것.  
- IR→Tiling→MemoryPlan→Schedule→CMDQ→ISA→Cycle Loop 전 과정을 하나의 pipeline으로 연결하는 공통 예제(LLaMA block 등)를 정의해, 여러 design 문서에서 동일 예제를 참조하도록 할 것.

---

## 4. Process / Test 계층

### Process 문서 (`docs/process/*.md`)

**역할 요약**  
Spec-Driven Development 워크플로우, 기여/리뷰 가이드, 네이밍 규칙, 버전 관리 정책 등을 정의하는 프로세스 문서.

**강점**  
- Spec → Design → Test → 구현 → 리뷰 흐름을 명시해 문서 우선 개발 문화를 뒷받침함.
- PR/Issue 리뷰 기준, 네이밍 컨벤션, Spec↔코드 버전 매핑 정책을 문서화해 팀 단위 개발에 적합한 기반을 제공함.

**개선 제안 (v1+v2 통합)**  
- GitHub PR 템플릿/Issue 템플릿과 연동되는 예시(예: Spec 변경 PR prefix, 필수 체크리스트)를 간단히 추가할 것.  
- Naming guide에는 “나쁜 이름 → 좋은 이름” 안티 패턴 예시를 몇 개 넣어 실제 코드 리뷰에 활용할 수 있게 할 것.

### Test 문서 (`docs/test/*.md`)

**역할 요약**  
테스트 계획, Unit/Integration/Performance/Golden 테스트 스펙, 대표 ONNX 모델과 메트릭 정의 등을 포함하는 테스트 계층.

**강점**  
- 시스템 전체 범위와 포함/제외 항목을 정리하는 상위 test_plan과, unit/integration/perf/golden 등 세부 스펙이 분리되어 있음.  
- trace 기반 golden reference 개념을 도입해, 시뮬레이터/컴파일러 변경 시 회귀 검증을 할 수 있는 구조를 마련함.

**개선 제안 (v1+v2 통합)**  
- 각 테스트 타입(Unit/Integration/Performance/Golden)에 대해 대표 ID와 대응하는 Spec/Design 항목을 표로 매핑해 추적 가능한 구조를 만들 것.  
- ONNX toy 모델들(MLP, 작은 Transformer block 등)과 각 모델에서 보는 메트릭(사이클 수, BW, SPM 사용률, 허용 오차)을 명시하고, baseline trace/metric 보관 위치를 정의할 것.

---

## 5. 전역 아키텍처 관점 요약 및 다음 단계 (v2 통합)

**주요 문제점 요약 (v2 기준)**  
1. 모듈별 설계 문서는 있으나, IR/Compiler/Simulator/Tracer를 하나의 global 아키텍처로 묶어 보여주는 전역 통합 그림이 부족함.  
2. IR → Tiling → Memory Plan → Schedule → CMDQ → ISA → Cycle Loop 단계 연결이 여러 문서에 흩어져 있어, 파이프라인을 한 번에 따라가기 어려움.  
3. TE/VE/DMA/SPM/DRAM timing 모델과 contention/bandwidth/stall 모델의 연계가 충분히 명시되지 않음.  
4. 많은 문서가 여전히 skeleton 수준으로 남아 있어, 실제 구현 세부 규칙(상태 전이, cost function 등)이 부족함.  
5. Trace & Visualizer 문서가 미완성 상태라, 시각화/분석 워크플로우가 아직 end-to-end로 닫혀 있지 않음.

**전략적 개선 방향 (Phase 제안)**  
- **Phase 0: Overview 계층 강화**  
  - `docs/overview/*` 및 신규 overview 문서를 통해 system/dataflow/memory+NoC/devflow overview를 정리하고, README/README_SPEC와 연결되는 “Documentation Reading Guide”를 제공한다.  
- **Phase 1: IR/ISA/CMDQ/Schedule/Timing pipeline 정합성 확보**  
  - IR 스펙, CMDQ/ISA 스펙, Timing 스펙, 주요 design 문서(StaticScheduler, CmdqGenerator, CycleLoop 등)를 하나의 파이프라인으로 정렬하고, LLaMA block 등의 공통 예제를 기반으로 end-to-end artefact 흐름을 문서화한다.  
- **Phase 2: Design / Test / Trace 디테일 보강**  
  - 각 design 문서의 상태/Owner/다이어그램/의사코드를 보강하고, test 문서와의 ID 매핑을 정리하며, Trace/Visualizer 요구사항과 예제를 확장해 분석 워크플로우를 완성한다.
