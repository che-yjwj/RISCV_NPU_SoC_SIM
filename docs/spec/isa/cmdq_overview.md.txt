

# CMDQ Overview  
**Path:** `docs/spec/isa/cmdq_overview.md`  
**Version:** v1.0  
**Status:** Stable Draft  
**Owner:** ISA Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **Command Queue (CMDQ)** 의 개념적 개요, 설계 철학, 구성 구조, 실행 모델을 설명한다.  
세부적인 필드 정의 및 JSON 스펙은 별도 문서인  
`docs/spec/isa/cmdq_format_spec.md` 에서 정의되며,  
본 문서는 **CMDQ가 시스템 전체에서 어떤 역할을 수행하는지**,  
**왜 CMDQ 기반 정적 실행 모델이 필요한지**,  
**NPU Simulator에서 CMDQ가 어떻게 동작하는지**를 설명한다.

CMDQ Overview는 ISA 스펙의 최상위 개념 문서로서  
Offline Compiler, NPU Simulator, Trace/Visualizer 개발 전 반드시 참조해야 한다.

---

# 2. CMDQ의 근본 개념 (What is CMDQ?)

CMDQ(Command Queue)는 **NPU가 실행해야 할 모든 연산을 정적으로 서술한 명령 스트림**이다.

- 일반 CPU ISA처럼 instruction-by-instruction 실행하는 것이 아니라  
- **Offline Compiler가 IR/Tiling/Scheduling 결과를 완전히 결정한 후**  
- 결과를 순차적 명령 리스트(JSON 포맷)로 기록한 것이 CMDQ다.

즉,

> “NPU의 실행을 완전히 결정하는, 오프라인 생성되는 작은 프로그램(program).”

이고,

> “런타임에 NPU 내부에는 복잡한 스케줄러가 필요 없다.”

라는 철학을 따른다.

### CMDQ는 다음 세 가지 조건을 만족해야 한다:

1. **정적 스케줄링의 모든 결과를 표현할 수 있어야 하고**  
2. **NPU 엔진(TE, VE, DMA)의 실제 자원 모델과 조화롭게 맞아야 하며**  
3. **Simulator가 cycle-based로 실행할 수 있도록 명령의 실행 의미가 명확해야 한다.**

---

# 3. CMDQ가 필요한 이유 (Why CMDQ?)

### 3.1 이유 1: Mobile/Edge NPU는 **정적 스케줄링**이 기본 철학  
Mobile NPU는 전력·면적·제어부 단순화를 위해  
런타임 스케줄러(DAG executor)를 사용하지 않는다.

- TE/VE/DMA는 단순한 finite-state machine  
- 명령이 들어오면 수행 → 완료 → 다음 명령  
- 복잡한 scheduling logic은 전부 offline에서 해결

이 구조를 그대로 반영한 것이 CMDQ 기반 실행이다.

---

### 3.2 이유 2: 타일 기반 병렬 처리 지원  
NPU는 tile-level parallelism이 핵심이다.

- multi-TE  
- multi-VE  
- multi-DMA channel  
- banked SPM  

이를 정확히 실행하려면 “tile 단위 명령”이 필요하다.  
CMDQ는:

- DMA_LOAD_TILE  
- TE_GEMM_TILE  
- VE_LAYERNORM_TILE  
- DMA_STORE_TILE  

과 같은 타일 단위 명령을 담아 tile parallelism을 직접적으로 표현한다.

---

### 3.3 이유 3: Timing simulator와 자연스럽게 연결  
Cycle-based simulator는 “명령 단위 이벤트”를 필요로 한다.

CMDQ는:

- 명령 시작(start cycle)  
- 명령 종료(end cycle)  
- 각 엔진의 busy/free 상태  
- DRAM/SPM traffic 발생 지점  

을 자연스럽게 추출할 수 있게 한다.

이는 trace와 시각화(Gantt, bandwidth heatmap)를 구성하는 기반이 된다.

---

### 3.4 이유 4: Mixed precision / KV cache / LLM 워크로드 표현  
CMDQ는 bitwidth-aware & LLM-friendly한 ISA이다.

예:

- W/A/KV 각기 다른 qbits  
- int4 / int8 / fp16 tile DMA  
- Q/K/V projection  
- KV cache tile append  
- softmax tile  
- head parallelism

이 모든 것을 **세부적인 opcode + 필드 조합**으로 명확하게 표현할 수 있다.

---

# 4. CMDQ의 구성 요소 (CMDQ Structure)

CMDQ는 아래와 같은 구조를 가진다:

CMDQ
├── Entry[0]
├── Entry[1]
├── Entry[2]
├── ...
└── Entry[N]


각 Entry는 아래 5가지 카테고리 중 하나이다:

1. **DMA Instructions**  
2. **Tensor Engine (TE) Instructions**  
3. **Vector Engine (VE) Instructions**  
4. **Sync / Control Instructions**  
5. **LLM Special Instructions (확장용)**  

이들 명령은 정적 스케줄링을 수행한 TileGraph → Scheduling DAG → CMDQ로 flatten 된 결과다.

---

# 5. CMDQ 실행 모델 (Execution Model)

CMDQ의 실행은 **Control FSM → Engine → Trace**의 구조로 동작한다.

아래는 전체 실행 모델을 텍스트 기반 다이어그램으로 나타낸 것이다.

CMDQ[0] → ControlFSM → (issue) → DMAEngine → trace
CMDQ[1] → ControlFSM → (issue) → DMAEngine → trace
CMDQ[2] → ControlFSM → (issue) → TensorEngine(TE0) → trace
CMDQ[3] → ControlFSM → (issue) → TensorEngine(TE1) → trace
CMDQ[4] → ControlFSM → (issue) → VectorEngine(VE0) → trace
...
CMDQ[N] = END → ControlFSM → HALT


### 핵심 포인트

1. **ControlFSM은 CMDQ를 한 줄씩 읽는다.**  
2. **deps_before** 필드를 체크하여 issue 가능한지 판단한다.  
3. 각 명령은 대응되는 엔진(queue)에 전달된다.  
4. 엔진들이 실제로 연산/메모리 동작을 수행한다.  
5. 완료 시 이벤트가 trace에 기록된다.  
6. END 명령을 만나면 실행 종료.

즉,

> ControlFSM은 **“제어”**만 하고,  
> 실제 compute/memory 실행은 모두 **엔진들(DMA/TE/VE)**이 담당한다.

---

# 6. CMDQ가 표현할 수 있는 것들

CMDQ는 단순한 명령 리스트가 아니라  
**정적 스케줄링 정보의 모든 결정 사항**을 포함한다.

### 6.1 Data movement (DMA)

- DRAM ↔ SPM  
- multi-bank SPM  
- bitwidth-aware tile load/store  
- 1D/2D stride load/store

### 6.2 Compute (TE/VE)

- GEMM tile  
- LN tile  
- Softmax tile  
- GELU tile  
- QKV projection tile  
- head parallelism

### 6.3 Synchronization

- deps_before 기반 tile dependency  
- barrier  
- tile-level ordering constraints  
- pipeline 적재/소비 관계 표현

### 6.4 Memory Allocation

- spm_bank / spm_offset  
- IFM/WGT/OFM의 tile-level SPM occupancy  
- bank conflict 모델링 기반 address-level granularity 제공

### 6.5 Mixed Precision

- qbits(W/A/KV)  
- TE/VE/DMA 명령별 bitwidth 적용  
- int4/int8 tile DMA → bandwidth 차이 반영  
- KV cache의 별도 bitwidth 표현

### 6.6 LLM Workload

- KV cache read/write tile  
- attention score matmul tile  
- per-head parallel tile  
- seq 증분 업데이트 tile  
- softmax tile  
- rotary embedding/normalization tile (추가 가능)

---

# 7. CMDQ 생성 과정 요약 (Compiler → CMDQ)

CMDQ는 다음 단계를 거쳐 생성된다.

ONNX Model
↓
IRBuilder
↓
Quantization Annotator (W/A/KV bit)
↓
TilingPlanner (TileGraph)
↓
SPMAllocator (bank/offset)
↓
StaticScheduler (tile-level DAG)
↓
CMDQGenerator (flattened JSON)


- TilingPlanner는 tile 크기/개수 생성  
- StaticScheduler는 TE/VE/DMA tile ordering 결정  
- CMDQGenerator는 tile-level 연산을 CMDQ entry로 serialize

이렇게 생성된 CMDQ는 **시뮬레이터의 유일한 입력**이다.

---

# 8. CMDQ와 Simulator의 관계 (핵심 개념)

### ✔ Simulator는 CMDQ를 실행할 뿐이다.  
### ✔ CMDQ가 곧 프로그램이며, 데이터플로우의 모든 내용이 미리 정해져 있다.  
### ✔ Simulator는 CMDQ를 cycle 단위로 해석하며 latency/resource/bandwidth를 계산한다.

이를 통해 다음이 가능해진다:

- 병목(bottleneck) 분석  
- engine utilization 분석  
- DRAM bandwidth saturation 여부 확인  
- tile parallelism 효과 검증  
- quantization에 따른 성능 영향 분석  
- LLM KV cache traffic 확인

---

# 9. CMDQ 명령 카테고리 개요

아래는 명령 카테고리별 개요이다（세부 필드는 format spec 문서에 있음）:

### 9.1 DMA Class
- `DMA_LOAD_TILE`  
- `DMA_STORE_TILE`

### 9.2 Tensor Engine (TE) Class
- `TE_GEMM_TILE`  
- `TE_CONV_TILE` (옵션)  
- `TE_MUL_TILE` (확장용)

### 9.3 Vector Engine (VE) Class
- `VE_LAYERNORM_TILE`  
- `VE_SOFTMAX_TILE`  
- `VE_GELU_TILE`

### 9.4 Control / Sync Class
- `BARRIER`  
- `NOP`  
- `END`

### 9.5 LLM-Specific Class (확장)
- KV cache load/store  
- attention tile  
- Q/K/V projection tile  
- rotary embedding tile  

---

# 10. CMDQ의 주요 특징 (Key Properties)

| 특징 | 설명 |
|------|------|
| 정적 스케줄링 기반 | runtime DAG scheduler 필요 없음 |
| Tile-friendly | tile 단위 데이터 배치, tile-level parallelism 표현 |
| Engine-aware | TE/VE/DMA 엔진을 직접 address |
| Bitwidth-aware | quantization 정책이 DMA/TE/VE에 직접 반영 |
| SPM-aware | spm_bank/spm_offset 포함 |
| Memory-accurate | DRAM/bus contention modeling 가능 |
| LLM-friendly | KV cache, attention을 명확히 표현 가능 |
| Trace-friendly | timeline, bandwidth, utilization 추출 용이 |

---

# 11. CMDQ와 xNPU ISA의 관계

CMDQ는 **xNPU ISA의 고수준 명령어 표현체**이며,  
컴파일러한테 친화적인 JSON 기반 ISA이다.

- 실제 하드웨어에서는 바이너리 인코딩 ISA를 사용할 수 있지만  
- 시뮬레이터에서는 **사람이 읽을 수 있는 JSON CMDQ**로 유지하는 것이  
  분석, 디버깅, 시각화 측면에서 훨씬 유리하다.

즉,

> 실제 하드웨어의 low-level ISA ↔ 소프트웨어/분석용 high-level CMDQ  
> 두 계층을 분리한다.

---

# 12. CMDQ 예시 (High-Level)

예시:

```json
[
  { "opcode": "DMA_LOAD_TILE", "tensor_role": "activation", "qbits": 8, "dram_addr": 1000, "spm_bank": 0 },
  { "opcode": "DMA_LOAD_TILE", "tensor_role": "weight", "qbits": 4, "dram_addr": 2000, "spm_bank": 1 },
  { "opcode": "TE_GEMM_TILE", "te_id": 0, "m": 64, "n": 128, "k": 256 },
  { "opcode": "VE_LAYERNORM_TILE", "ve_id": 1, "length": 128 },
  { "opcode": "DMA_STORE_TILE", "tensor_role": "activation", "qbits": 8, "dram_addr": 3000 },
  { "opcode": "END" }
]
각 명령은:

특정 엔진에 의해 실행되고

timing/latency/bandwidth trace를 생성하게 된다.

13. CMDQ가 갖는 장점 (Advantages)
✔ 개발자와 아키텍트에게
분석/프로파일링에 매우 유리

병렬성 관찰 용이 (multi-TE/VE)

bitwidth 변화 실험이 간단

✔ Compiler 개발자에게
명령 생성 규칙이 명확하므로 테스트가 쉬움

스케줄링/타일링 알고리즘의 효과가 즉시 반영됨

✔ Simulator 개발자에게
ControlFSM logic이 단순 (fetch → deps check → issue)

cycle-based 타이밍 모델과 직접 연결

✔ 모델 아키텍트에게
KV cache 크기/traffic 변화가 명확히 보임

attention/head parallelism 효과가 쉽게 보임

14. CMDQ 확장성 (Extensibility)
CMDQ는 “spec-driven 확장”을 원칙으로 한다.

새 TE/VE 엔진이 도입되면 새로운 opcode 추가 가능

새 양자화 방식, int2/int1 등 도입 시 qbits 확장 가능

sparsity engine이 도입되면 SPARSE_TILE opcode 추가

new memory ops (gather/scatter) 확장 가능

encoder/decoder LLM 구조에 각각 특화된 tile opcode 추가 가능

핵심은:

기존 명령의 의미는 바꾸지 않고, 새로운 용도는 새로운 opcode로 정의한다.

15. 결론 (Summary)
cmdq_overview.md는 CMDQ의 전체 개념과 실행 모델을 정의하는
ISA 레이어의 최상위 문서이다.

이 문서의 핵심 메시지는 다음과 같다.

CMDQ는 정적 스케줄링 기반 NPU 실행의 핵심 인터페이스다.

CMDQ는 DMA/TE/VE tile-level 명령을 통해 전체 모델 실행을 기술한다.

CMDQ는 mixed precision, SPM allocation, TileGraph, LLM workload를 모두 반영한다.

Simulator는 CMDQ를 기반으로 cycle-based 실행을 수행하여
latency · bandwidth · utilization을 정밀하게 분석할 수 있다.

CMDQ는 오프라인 컴파일러와 시뮬레이터 사이의
가장 중요한 연결점이며,
전체 프로젝트의 “ISA-level heartbeat”로 동작한다.