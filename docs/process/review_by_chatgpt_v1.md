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

## 1. 상위 Spec 인덱스

### `docs/README_SPEC.md`

**역할 요약**  
`docs/` 아래 전체 문서들의 카탈로그 + 읽기 순서 정의.

**강점**  
- overview / spec / design / process / test로 계층이 잘 나뉘어 있고, 각 폴더의 역할이 명확함.
- “먼저 읽어야 할 문서 → 이후 상세 스펙” 순서가 잡혀 있어 SDD(Spec-Driven Development)에 적합한 인덱스 구조.

**개선 제안**  
- 각 문서에 “필수 / 권장 / 참고” 레벨 태그를 달면, 새 기여자가 어디까지 읽어야 할지 더 명확해짐.
- 문서 간 의존 관계를 간단한 표(예: “IR Spec ← Quantization IR Extension ← Tiling Planner Design…”)로 추가하면 전체 그래프가 더 선명해짐.

---

## 2. Overview 계층

### `docs/overview/system_architecture.md`

**역할 요약**  
오프라인 컴파일러 + NPU 시뮬레이터 전체 아키텍처를 정의하는 상위 문서.

**강점**  
- 목적/범위/테스트 항목까지 포함하는 “mini PRD + SDD” 역할을 잘 수행하고 있음.
- IRBuilder, Tiling, StaticScheduler, CmdqGenerator, Simulator Core, TraceEngine 등 주요 블록이 모두 등장해서 big picture가 분명함.

**개선 제안**  
- RISC-V SoC 관점에서 CPU/AXI/인터럽트/메모리 계층과의 연결을 블록 다이어그램(텍스트 기반이라도)으로 더 명시하면 SoC 관점 독자에게도 좋음.
- Prefill/Decode 워크로드 분리, 모바일 NPU 특유의 제약(전력/열 등)을 high-level 비기능 요구사항으로 2–3줄 추가하면 타깃이 더 분명해짐.

---

### `docs/overview/dataflow_overview.md`

**역할 요약**  
ONNX → IR → TileGraph → CMDQ → Simulator로 이어지는 데이터 플로우를 설명.

**강점**  
- 어떤 아티팩트가 어느 단계에서 생성/소비되는지 구조가 잘 잡혀 있음.
- IR 노드, 텐서, 타일, CMDQ 엔트리 사이의 관계를 상위 레벨에서 이해하기 좋음.

**개선 제안**  
- 대표 예시(예: 단일 MatMul + GELU 블록)를 가지고 ONNX → IR → TileGraph → CMDQ까지 단계별로 한 줄씩 보여주는 end-to-end 예제를 하나 넣으면 좋음.
- KV cache / prefill-decode 분리 데이터플로우를 별도 subsection으로 정리하면 LLM 전용 플로우를 읽는 데 도움이 됨.

---

### `docs/overview/module_responsibilities.md`

**역할 요약**  
각 모듈(compiler/simulator/trace 등)의 책임 범위를 정의하는 문서.

**강점**  
- 모듈별 input/output과 “하지 말아야 할 일”까지 나누는 방향성이 좋음.
- Simulator Core에서 타이밍 모델 변경을 하지 않는다 등의 설계 원칙이 드러남.

**개선 제안**  
- StaticScheduler vs CmdqGenerator vs ControlFSM 사이의 경계를 RACI 표(Responsible/Accountable/Consulted/Informed) 형태로 정리하면 구현 분리가 더 직관적일 것.
- VE/TE/DMA/MemoryModel 간 책임(예: bank conflict 계산 위치)을 한 줄씩 더 구체화하면 하드웨어 모델링 시 혼란이 줄어듦.

---

## 3. IR 스펙 계층

### `docs/spec/ir/npu_ir_spec.md`

**역할 요약**  
내부 NPU IR의 전체 구조·노드/텐서 스키마·타일 변환 규칙을 정의하는 핵심 스펙.

**강점**  
- “IR이 단일 source of truth”라는 선언이 명시적이라 컴파일러 설계 방향성이 깔끔함.
- LLM 친화 요소(KV cache, attention op, mixed precision 등)를 고려한 설계 철학이 잘 드러남.

**개선 제안**  
- IR 노드 타입(예: MatMul, Conv, Attention, Load/Store 등)에 대한 표 형식 요약(필드, 속성, 제약조건)을 추가하면 구현자가 참조하기 좋음.
- IR 버전닝 정책(필드 추가/제거 시 호환성, IR version tag 등)을 짧게라도 명시해 두는 것이 바람직함.

---

### `docs/spec/ir/quantization_ir_extension.md`

**역할 요약**  
IR 레벨에서 quantization 정보를 표현하는 규칙(스케일, zero-point, bitwidth, per-tensor/per-channel 등)을 정의.

**강점**  
- Quantization 정보를 텐서/연산/특정 서브그래프(KV cache 등)에 어떻게 부착할지 범위가 잘 정리되어 있음.
- Mixed-precision과 IR 확장 간 연결을 명확히 하려는 의도가 보임.

**개선 제안**  
- `docs/spec/quantization/*.md`와 중복되는 개념은 “참조”로 몰고, IR 스펙에는 필드 정의와 life-cycle 위주로 최소셋만 남기는 편이 유지보수에 유리함.
- 실제 예시(예: 8-bit W, 8-bit A, 4-bit KV) IR 스니펫을 JSON 형태로 1–2개 추가하면 이해에 도움이 됨.

---

### `docs/spec/ir/tensor_metadata_spec.md`

**역할 요약**  
텐서 shape/layout/stride/메모리 위치 등 메타데이터 구조 정의.

**강점**  
- Tile/Block/Row-major 등 layout 정보를 IR 레벨에서 어떻게 표현할지 고민한 흔적이 있음.

**개선 제안**  
- `SPMAllocator`, `Timing SPM Model`과 공유해야 하는 필드(예: bank_id, offset, alignment)를 명시적으로 align해 두면 좋음.
- Broadcast, reshape, view 같은 “메타데이터만 바뀌는 연산”에 대한 규칙을 별도 섹션으로 정리하면 메모리 모델 구현이 단순해짐.

---

## 4. ISA / CMDQ 스펙

### `docs/spec/isa/cmdq_overview.md`

**역할 요약**  
CMDQ 개념, 역할, 실행 모델을 설명하는 상위 문서.

**강점**  
- “CMDQ = 정적 명령 스트림”이라는 개념과 필요성이 명확함.
- Offline Compiler / Simulator / Trace 관점에서 CMDQ를 어떻게 보는지 설명해 줌.

**개선 제안**  
- Prefill/Decode 워크로드에서 CMDQ를 어떻게 분리/공유할지(멀티 스트림 또는 단일 스트림 + phase tag 등)를 high-level로 한 문단 추가하면 LLM use-case와 더 잘 맞음.

---

### `docs/spec/isa/cmdq_format_spec.md`

**역할 요약**  
CMDQ 엔트리의 필드 정의, 형식, JSON 스펙 등 상세 포맷 정의.

**강점**  
- `deps_before`, `engine_type`, tiling 관련 필드 등을 중심으로 CMDQ를 ISA에 가깝게 formal하게 다룸.

**개선 제안**  
- 몇 개의 엔트리로 구성된 작은 예제 CMDQ(JSON)를 넣고, 각 필드에 대한 주석을 달면 Golden CMDQ 기준이 됨.
- 필드별 “필수/옵션/예약(reserved)” 구분을 표로 정의하면 확장성 측면에서 유리함.

---

### `docs/spec/isa/opcode_set_definition.md`

**역할 요약**  
CMDQ opcode 집합 정의(LOAD/STORE/TE_OP/VE_OP/WAIT 등).

**강점**  
- TE/VE/DMA 각각에 대한 opcode 그룹을 나누는 구조가 합리적임.

**개선 제안**  
- 각 opcode와 IR op의 1:1 또는 1:N 매핑 표를 추가하면 IR-to-CMDQ 단계 설계에 도움됨.
- 향후 extension(예: custom micro-kernel opcode)용 reserved opcode 범위를 명시하면 더 “ISA다운” 스펙이 됨.

---

## 5. Timing 스펙 계층

### `docs/spec/timing/dma_timing_spec.md`

**역할 요약**  
DMAEngine의 latency/bandwidth/contention 모델 정의.

**강점**  
- bus width, burst, bank conflict, multi-channel contention 등을 모두 고려 대상으로 둔 점이 좋음.
- tile-level granularity에 최적화된 latency 모델이라는 방향성이 분명함.

**개선 제안**  
- 실제 시뮬레이션에서 사용할 파라미터 config 예시(JSON)를 하나 넣으면, 구현자가 spec → 코드 매핑을 쉽게 할 수 있음.
- 모바일 LPDDR / 서버 HBM 등 여러 프로파일을 지원할 계획이라면, profile 개념을 간단히 언급해 두는 것도 좋음.

---

### `docs/spec/timing/te_timing_spec.md`, `ve_timing_spec.md`

**역할 요약**  
TE/VE 연산의 pipeline/latency 모델 정의.

**강점**  
- TE(텐서 엔진)와 VE(벡터 엔진)를 분리해 timing을 정의하는 구조가 잘 맞음.

**개선 제안**  
- TE/VE 각각에 대해 “throughput bound vs latency bound” 시나리오를 간단한 예제로 1개씩 추가하면 시뮬레이터 결과 해석에 도움이 됨.
- 명시된 timing 모델과 실제 하드웨어(예: HotChips 포스터 구조) 사이 대응 관계를 한 줄씩 적어 주면 real chip과 align할 때 좋음.

---

### `docs/spec/timing/spm_model_spec.md`

**역할 요약**  
SPM(Scratchpad) 용량, bank 구조, access latency 모델 정의.

**강점**  
- bank conflict, multi-port 여부 등을 모델링 대상으로 둔 점이 좋음.

**개선 제안**  
- “logical bank index 계산식”을 pseudo-code로 명시하면 SPMAllocator와 Simulator가 동일 규칙을 쓰는지 검증하기 쉬움.

---

### `docs/spec/timing/bus_and_noc_model.md`

**역할 요약**  
Bus 및 NoC 타이밍/대역폭/컨텐션 모델 정의.

**강점**  
- 단일 bus와 간단한 NoC 계층 구조를 모두 포괄할 수 있는 열린 구조로 설계할 수 있음.

**개선 제안**  
- SoC 수준에서 DRAM/CPU/NPU/IO 간 트래픽 시나리오를 하나라도 예시로 넣으면, 향후 SoC-level 모델링 확장 시 기준이 됨.

---

## 6. Quantization 스펙 계층

### `docs/spec/quantization/quantization_model_overview.md`

**역할 요약**  
전체 양자화 모델(범용 개념, W/A/KV 등)을 설명하는 상위 문서.

**강점**  
- bitwidth/mode/scheme 등을 정리하려는 상위 구조가 좋음.

**개선 제안**  
- IR/ISA와의 연결 지점을 명확히 하기 위해, “IR 필드와 매핑표”를 별도 섹션으로 추가하면 좋음.

---

### `docs/spec/quantization/bitwidth_memory_mapping.md`

**역할 요약**  
bitwidth가 실제 메모리 사용량에 어떻게 반영되는지(예: 4bit packing, alignment 등) 정의.

**강점**  
- 시뮬레이터가 “성능 + 용량”을 동시에 보는 데 필요한 요소를 잘 잡고 있음.

**개선 제안**  
- 예: 4b × 64 element 텐서를 32/64/128-byte alignment에 맞춰 패킹하는 구체 예시를 추가하면 구현 난이도가 크게 줄어듦.

---

### `docs/spec/quantization/kv_cache_quantization_spec.md`, `mixed_precision_policy.md`

**역할 요약**  
KV cache 전용 양자화, mixed-precision 정책 정의.

**강점**  
- LLM 모바일 NPU 타깃에서 중요한 부분을 별도 문서로 뺀 것이 좋음.

**개선 제안**  
- KV cache quant와 일반 activation quant 차이를 비교표로 정리하면 정책 검증이 쉬워짐.
- mixed-precision policy를 “rule-based 정책 pseudo-code”와 “config 예시”로 제공하면 오프라인 컴파일러 구현이 쉬움.

---

## 7. Trace / Visualization 스펙 계층

### `docs/spec/trace/trace_format_spec.md`

**역할 요약**  
trace 파일 포맷 정의(필드, 타입, 버전 등).

**강점**  
- trace를 versioned artifact로 다루려는 구조가 있어 viewer/툴 체인과의 호환성이 좋아짐.

**개선 제안**  
- 최소 1개의 full trace 예제(JSON)를 넣고, 상단에 backward compatibility 정책을 간단히 적어두면 좋음.

---

### `docs/spec/trace/gantt_timeline_spec.md`, `bandwidth_heatmap_spec.md`, `visualization_requirements.md`

**역할 요약**  
Gantt-style timeline · bandwidth heatmap 등 viewer 요구사항 정의.

**강점**  
- 시각화 관점까지 문서화한 점이 인상적이며, 일반 시뮬레이터 문서에서 자주 빠지는 부분을 잘 보완함.

**개선 제안**  
- 시각화에 필요한 최소 trace 필드를 단순 설명이 아니라 표(필드/타입/필수 여부)로 정의하면 TraceEngine 구현이 명확해짐.
- Prefill/Decode를 구분해 표시하는 규칙(색/태그 등)을 high-level 요구사항으로 적어두면 LLM 워크로드 분석에 도움이 됨.

---

## 8. Design 계층 (공통)

Design 문서는 구조와 톤이 거의 통일되어 있어, 공통 코멘트를 먼저 제시한다.

### 공통 강점

- Path / Status / Owner / Last Updated가 머리말로 통일되어 있어 SDD/리뷰 워크플로우에 적합함.
- “목적 → 책임 → 입출력 → 내부 구조 → 알고리즘” 순서로 구성된 문서가 많아, 실제 구현자가 바로 코드로 옮기기 좋음.
- 관련 Spec 문서를 상단에 링크하는 패턴이 매우 좋음.

### 공통 개선 제안

- 대부분 `Owner: TBD`, `Last Updated: YYYY-MM-DD` 상태이므로 구현이 시작되면 Owner 지정 + 날짜 업데이트가 필요함.
- 각 design 문서에 “구현 상태(미구현/부분 구현/완료)”를 간단한 상태 플래그로 추가하면 roadmap 파악이 쉬움.

---

### 대표 Design 문서별 포인트

#### `docs/design/npu_simulator_core_design.md`

- **요약**: Simulator Core의 서브모듈(ControlFSM, DMA/TE/VE, MemoryModel, Trace 등)과 global cycle loop 동작 정의.
- **강점**: Core에서 “하지 말아야 할 일(타이밍/리소스 모델 변경)”을 명시해 역할 분리가 분명함.
- **개선**: Global cycle loop pseudo-code를 한 블록에 집중시켜, `cycle_loop_design` 문서와 역할 경계를 더 명확히 할 수 있음.

#### `docs/design/cycle_loop_design.md`

- **요약**: Global cycle-based 시뮬레이터 루프의 상세 설계.
- **강점**: 여러 클럭 영역을 단일 전역 cycle로 수렴시키는 컨셉이 명확함.
- **개선**: DRAM vs NPU vs CPU clock 차이를 다루기 위한 sub-cycle 규칙이나 N:1 ratio 예시를 적어두면 좋음.

#### `docs/design/control_fsm_design.md`

- **요약**: CMDQ fetch/issue/complete를 관리하는 Control FSM 설계.
- **강점**: NOT_ISSUED/READY/ISSUED/COMPLETED 등 state를 명확히 다룸.
- **개선**: starvation-free 스케줄링 등 데드락/라이브락 방지 전략을 별도 섹션으로 명시하면 안정성이 강화됨.

#### `docs/design/cmdq_generator_design.md`

- **요약**: StaticScheduler 결과를 CMDQ 엔트리 스트림으로 직렬화하는 로직 설계.
- **강점**: IR/TileGraph와 CMDQ 필드를 연결하는 방향성이 명확함.
- **개선**: Golden CMDQ 예제를 통해 “IR → CMDQ 변환 규칙”을 몇 개 bullet로 정리하면 테스트 설계에 유리함.

#### `docs/design/ir_builder_design.md`

- **요약**: ONNX → NPU IR 변환기 설계.
- **강점**: 지원 ONNX op-set subset 정의와, 미지원 op 처리 전략을 문서화하기 좋은 구조.
- **개선**: ONNX 버전·지원 op-list를 표로 뽑으면 호환성 체크리스트로 사용 가능.

#### `docs/design/tiling_planner_design.md`

- **요약**: IR 레벨에서 타일링 전략을 결정하는 모듈 설계.
- **강점**: tile size 결정, SPM 제약 반영, TE/VE 병렬성 활용 관점에서 핵심 위치.
- **개선**: 1D/2D/attention-like 연산 각각에 대해 예시 타일링 전략을 표/그림으로 넣으면 정책 구현에 도움됨.

#### `docs/design/spm_allocator_design.md`

- **요약**: SPM bank/offset allocator 알고리즘 설계.
- **강점**: bank conflict 최소화, reuse 등 중요한 요소를 문서화할 수 있는 좋은 위치.
- **개선**: 단일 tile graph에 대한 SPM 배치 예시를 표/그림으로 넣어 결과를 시각화하면 해석이 쉬움.

#### `docs/design/static_scheduler_design.md`

- **요약**: TileGraph + SPM allocation + 엔진 구성을 입력으로 정적 스케줄 DAG 생성.
- **강점**: 입력/출력 정의가 명확하고, deps_before → CMDQ deps 필드로 이어지는 구조가 잘 보임.
- **개선**: scheduler의 우선순위 정책(예: DMA 우선, TE 채움, VE overlap)을 pseudo-code로 서술하면 baseline이 명확해짐.

#### `docs/design/te_engine_design.md`, `ve_engine_design.md`

- **요약**: TE/VE 내부 파이프라인과 연산 모델 설계.
- **강점**: 대규모 matmul(TE) vs scalar/vector(VE) 역할 분리가 모바일 NPU 모델링에 적합.
- **개선**: TE → VE 후처리 hand-off 시퀀스를 시퀀스 다이어그램으로 보여주면 data path 이해가 쉬움.

#### `docs/design/dma_engine_design.md`

- **요약**: DMAEngine 구조/큐/상태머신 설계.
- **강점**: Timing spec과 자연스럽게 연결될 수 있는 구조.
- **개선**: DRAM read/write, prefetch, invalidate 등 DMA 명령 유형별 상태 전이를 표/도식으로 정리하면 좋음.

#### `docs/design/offline_compiler_design.md`

- **요약**: 전체 오프라인 컴파일러 파이프라인 설계.
- **강점**: IRBuilder / Tiling / SPMAllocator / StaticScheduler / CmdqGenerator가 하나의 흐름으로 잘 묶임.
- **개선**: pass graph(노드=pass, edge=순서)를 그려 multi-pass optimization 확장 여지를 열어 두면 좋음.

#### `docs/design/visualizer_design.md`

- **요약**: trace 기반 visualizer 설계.
- **강점**: Spec/Trace 문서와 자연스럽게 연결되는 엔트리 포인트.
- **개선**: 시각화 대상(TE/VE/DMA timeline, SPM usage, DRAM BW 등)을 “MVP vs 확장”으로 나눠 우선순위를 명시하면 구현 로드맵에 유용함.

---

## 9. Process 계층

### `docs/process/spec_driven_development_workflow.md`

**강점**  
- Spec → Design → Test → 구현 → 리뷰 흐름이 잘 정의되어 있고, 문서 우선 원칙이 명확함.

**개선 제안**  
- GitHub PR 템플릿/Issue 템플릿과 연동되는 예시(“Spec 변경 시 PR 타이틀 prefix” 등)를 추가하면 실제 워크플로에 바로 쓸 수 있음.

---

### `docs/process/contribution_and_review_guide.md`

**강점**  
- 리뷰 관점, 코멘트 스타일 등을 명시하기 좋은 위치.

**개선 제안**  
- 최소 리뷰어 수, 승인 규칙, “Spec 변경 vs 구현 변경”의 리뷰 기준을 간단히 명시하면 팀 개발에 더 적합해짐.

---

### `docs/process/naming_convention.md`

**강점**  
- IR/CMDQ/trace 필드 이름과 코드 네이밍을 align시키는 데 중요한 문서.

**개선 제안**  
- 안티 패턴 예시(나쁜 이름 → 좋은 이름)를 몇 개 넣어주면 실무에서 유용함.

---

### `docs/process/versioning_and_changelog_guide.md`

**강점**  
- 스펙 변경이 잦은 초기 단계에 특히 중요함.

**개선 제안**  
- Spec version과 code tag를 어떻게 맞출지(예: spec v1.1 → 코드 태그 v0.3.x)를 간단히 정책화하면 관리에 도움이 됨.

---

## 10. Test 계층

### `docs/test/test_plan.md`

**강점**  
- 시스템 전체 범위, 포함/제외 항목을 정리하기 좋은 상위 문서.

**개선 제안**  
- 각 테스트 타입(Unit/Integration/Performance/Golden)에 대해 대표 ID 하나씩 구체 예를 적으면, 다른 test 문서와의 연결이 분명해짐.

---

### `docs/test/unit_test_spec.md`

**강점**  
- 모듈별 단위 테스트 정의에 적합한 구조.

**개선 제안**  
- design 문서 각 섹션(예: StaticScheduler 알고리즘)에 대해 “필수 unit test list”를 표로 매핑해 두면 좋음.

---

### `docs/test/integration_test_spec.md`

**강점**  
- Compiler + Simulator 전체 플로우를 검증하는 케이스를 담기 좋음.

**개선 제안**  
- ONNX toy 모델들(MLP, 작은 Transformer block 등)을 명시하고, 각 모델에 대해 어떤 메트릭(사이클 수, BW, SPM 사용률)을 체크할지 적어두면 좋음.

---

### `docs/test/performance_validation_protocol.md`

**강점**  
- 성능 검증 프로토콜을 분리해 둔 점이 좋음.

**개선 제안**  
- “성능 회귀 기준”(예: ±5% 이내면 OK)을 명확히 하고, baseline trace/metric을 어디에 보관할지까지 정의하면 자동화에 도움이 됨.

---

### `docs/test/golden_trace_examples.md`

**강점**  
- trace 기반 golden reference 개념이 잘 살아 있음.

**개선 제안**  
- 최소 1–2개의 실제 trace 스니펫(축약형)을 넣어, 어떤 필드를 기준으로 golden을 비교할지 구체적으로 보여주면 좋음.

---

## 11. 전체 총평 및 다음 단계 제안

- 전체적으로 **실제 회사 내부 SDD 기반 아키텍처 문서 수준에 근접한 구조**를 가지고 있음.
- 구조는 충분히 잘 잡혀 있으므로, 다음과 같은 정제를 추천함:
  1. 각 문서의 **Owner / Last Updated / Status(미구현/부분 구현/완료)** 갱신  
  2. 대표 예제(ONNX → IR → Tile → CMDQ → Trace) 몇 개를 공통 레퍼런스로 여러 문서에 걸쳐 삽입  
  3. Test 문서와 Design/Spec 문서 사이의 **ID 매핑(테스트 케이스 ↔ 스펙 항목)** 정리

이 세 가지를 채워 넣으면, 바로 구현·연구용 레포로 활용하기 좋은 문서 스택이 될 것이다.