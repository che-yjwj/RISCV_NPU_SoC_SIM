# Quantization IR Extension Specification  
**Path:** `docs/spec/ir/quantization_ir_extension.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** IR / Quantization Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU IR(NPU Intermediate Representation)** 에  
정교한 **Quantization Annotation Layer**를 추가하기 위한 확장 스펙이다.

본 확장은 다음 요구사항을 충족하기 위해 설계되었다:

- **Mixed Precision 지원**  
  - Weight bitwidth (W-bit)  
  - Activation bitwidth (A-bit)  
  - KV Cache bitwidth (KV-bit)  
  - Layer별/Tile별 bitwidth 독립 설정  

- **Memory-accurate 타일링 모델**과 연동  
  - qbits → byte size → DMA latency → SPM allocation과 직접 연결  

- **LLM-friendly Quantization Workflow** 지원  
  - KV Cache만 별도의 bitwidth 사용 가능  
  - Q/K/V projection의 weight/activation bit별 제어  
  - head parallelism 기반 tile quantization  

- **IR, TileGraph, CMDQ 전 단계에 영향을 주는 핵심 메타데이터** 제공

본 문서는 Quantization Annotation을  
**IR 확장 레이어로 공식 정의**한다.  

---

# 2. 설계 원칙 (Design Principles)

Quantization IR Extension은 다음 원칙을 따른다.

### ✔ 2.1 IR은 “bitwidth 표현만 담당”  
scale, zero-point, dequant 등 실제 수치적 quantization은  
Runtime/Kernel Library의 책임이며  
IR은 **bitwidth만을 구조화된 메타데이터로 표현**한다.

### ✔ 2.2 Mixed precision은 W/A/KV 세 가지 축을 독립적으로 설정  
각 LayerIR 내부에서:

- `qbits_weight`
- `qbits_activation`
- `qbits_kv`

세 필드는 모두 자유롭게 설정될 수 있으며 상호 독립이다.

### ✔ 2.3 bitwidth를 통해 memory traffic을 정확하게 계산  
`num_elements * qbits / 8` → DMA bytes  
→ DRAM bandwidth → tile latency → 전체 모델 latency

이 흐름을 IR부터 명백하게 표현한다.

### ✔ 2.4 LayerIR → TileGraph → CMDQ로 자연스럽게 전달  
Quantization annotation은 이후 파이프라인 단계에서  
타일링/SPM allocation/Scheduling/CMDQ 전부에 사용된다.

---

# 3. IR 내의 Quantization Annotation 구조

Quantization 정보는 LayerIR과 TensorIR에 다음과 같이 보관된다.

---

## 3.1 LayerIR 확장 필드

LayerIR 공통 스키마에 아래 세 필드를 추가한다.

```json
{
  "qbits_weight": 8,
  "qbits_activation": 8,
  "qbits_kv": null
}
```

의미
필드	설명
qbits_weight	해당 레이어의 weight bitwidth
qbits_activation	입력/출력 activation bitwidth
qbits_kv	KV cache 관련 연산에만 적용

기본 규칙

qbits_kv는 attention/KV 관련 레이어에만 사용

qbits_weight / qbits_activation은 대부분의 레이어에서 기본 적용

bitwidth는 tile-level로 override 가능

## 3.2 TensorIR 내 Quantization 필드
모든 TensorIR은 다음 필드를 갖는다.

```json
{
  "dtype": "fp32 | int8 | int4 | int2",
  "qbits": 8
}
```

dtype vs qbits
dtype은 저장 타입(메모리 표현)

qbits는 실제 quantization bitwidth

두 값은 동일할 필요 없음.
예: int4 dtype + qbits=4 (기본)
예: fp16 dtype + qbits=8 (activation 내부 quantization)

# 4. Layer별 Quantization Policy
IR Builder + Quantization Annotator 조합에서
각 LayerIR에 대해 특정 정책 기반으로 bitwidth가 설정된다.

## 4.1 GEMM / MatMul
W-bit: 2/4/8 가능

A-bit: 4/8 가능

출력 activation은 A-bit로 설정

KV-bit는 사용되지 않음

## 4.2 LayerNorm / RMSNorm
A-bit 중심

W-bit 없음 (gamma/beta만 FP or low-bit 가능)

LN tile 연산은 VE에서 실행되므로 VE latency는 A-bit에 비례

## 4.3 Softmax
A-bit 적용

exp/sum/normalize 구간은 int8 기반 확장 or hybrid precision 가능

tile-level에서 qbits-activation이 latency/byte-cost를 좌우

## 4.4 Q/K/V Projection
각 projection은 별도의 bitwidth를 가질 수 있음.

```text
Q_proj: W-bit=4, A-bit=8
K_proj: W-bit=4, A-bit=8
V_proj: W-bit=4, A-bit=8
```
이 정보는 3개의 GEMM tile에 각각 반영된다.

## 4.5 Attention Scores (Q · K^T)
A-bit 사용

head-specific tile quant도 가능

KV Cache는 별도 bitwidth 사용 가능

## 4.6 KV Cache Update
KV Cache만 특수 bitwidth 설정 가능:

예:

```json
{
  "qbits_activation": 8,
  "qbits_kv": 4
}
```
이는 DMA_LOAD_TILE / DMA_STORE_TILE에서
tensor_role="kv"로 반영됨.

# 5. Quantization 정보의 IR → TileGraph → CMDQ 전파 규칙
Quantization 정보는 전체 파이프라인에서 다음 규칙에 따라 전파된다.

## 5.1 IR 단계
LayerIR에 qbits 설정

TensorIR에 dtype/qbits 설정

shape/layout 정보와 함께 저장

## 5.2 TileGraph 단계
TileGraph는 다음 확장 정보를 tile node에 포함한다.

```json
{
  "tile_qbits_w": 4,
  "tile_qbits_a": 8,
  "tile_qbits_kv": null
}
```
TileGraph는 tile weight / tile activation 의 정확한 byte 수를 계산할 수 있어야 한다.

## 5.3 SPM Allocation 단계
spm_required_bytes = elements * qbits / 8

을 이용해 tile-level SPM occupancy를 계산한다.

bitwidth가 작으면:

한 bank에 더 많은 타일을 저장 가능

bank conflict를 줄일 기회 증가

DMA burst 요청 크기 감소

전체 latency 감소 가능

## 5.4 Static Scheduler
Scheduler는 bitwidth를 기반으로 다음 사항을 고려 가능:

DMA latency (low-bit tile은 빨리 끝남)

TE tile latency (packed weight일 경우 compute cycles 영향)

VE tile latency (vector length * qbits 영향)

즉, 스케줄러는 bitwidth을 보고 tile 순서를 재배치할 수 있다.

## 5.5 CMDQ Generator
CMDQ 엔트리에 bitwidth가 직접 기록된다.

예:

```json
{
  "opcode": "DMA_LOAD_TILE",
  "qbits": 4
}
```

```json
{
  "opcode": "TE_GEMM_TILE",
  "qbits_weight": 4,
  "qbits_activation": 8
}
```
Simulator는 해당 필드를 사용하여:

DMA bytes 계산

TE/VE latency 계산

DRAM bandwidth occupancy 계산

등을 수행한다.

# 6. Quantization Metadata 구조
Quantization 설정은 QConfig라는 독립 컨테이너에 보관될 수 있다.

## 6.1 QConfig 예시

```json
{
  "default": {
    "weight": 4,
    "activation": 8,
    "kv": 4
  },
  "override": {
    "q_proj": { "weight": 4, "activation": 8 },
    "k_proj": { "weight": 4, "activation": 8 },
    "v_proj": { "weight": 4, "activation": 8 },
    "kv_update": { "kv": 4 }
  }
}
```
QConfig는 IRBuilder 혹은 Quantization Annotator가 IR에 주입하는 데이터다.

# 7. Quantization-aware IR Example (Full LayerIR)
예시 LayerIR:

```json
{
  "id": "ffn_gemm1",
  "op_type": "GEMM",
  "inputs": ["hidden_1", "w1"],
  "outputs": ["ffn_out1"],
  "shape": { "M": 1024, "N": 4096, "K": 1024 },

  "qbits_weight": 4,
  "qbits_activation": 8,
  "qbits_kv": null
}
```
예시 KV Cache LayerIR:

```json
{
  "id": "kv_cache_append",
  "op_type": "KV_UPDATE",
  "inputs": ["k_new", "v_new", "kv_cache_base"],
  "outputs": ["kv_cache_out"],

  "qbits_weight": null,
  "qbits_activation": 8,
  "qbits_kv": 4
}
```

# 8. Quantization 흐름 총정리 (Dataflow)
텍스트 기반 다이어그램으로 표현:

```text
ONNX Model
     ↓
IRBuilder
     ↓
Quantization Annotator
     ↓
LayerIR + TensorIR (W/A/KV qbits 포함)
     ↓
TilingPlanner
     ↓
TileGraph (tile-level qbits 포함)
     ↓
SPMAllocator (qbits → bytes)
     ↓
Scheduler (latency influenced by qbits)
     ↓
CMDQGenerator
     ↓
CMDQ(qbits_* 필드 포함)
     ↓
Simulator (DMA/TE/VE timing 반영)
```
모든 단계가 quantization 정보를 활용하고 있으며
bitwidth 변화는 전체 성능/메모리 모델에 수준 높은 영향력을 가진다.

# 9. 확장성 (Extensibility)
Quantization IR 확장은 다음 확장을 자연스럽게 지원한다.

✔ 더 많은 bitwidth 추가
int2, int1, fp8, hybrid quant 등

qbits에 새로운 set을 추가하면 됨

✔ Sparsity-aware Quantization
sparsity pattern을 IR annotation으로 추가 가능

TileGraph와 CMDQ에 forwarding 가능

✔ Per-tile bitwidth override
layer-level qbits 외, tile-level qbits 추가

fine-grained mixed precision 지원 가능

✔ Mixed integer/floating bit-width
LayerNorm 등에서 internal fp16, output int8 등의 조합 허용

# 10. 결론 (Summary)
본 문서는 NPU IR의 Quantization Extension을 공식화한 문서로서,
정적 스케줄 기반 NPU 컴파일러 + 시뮬레이터에서 필요로 하는 모든 bitwidth 정보를
IR 레벨에서 구조적으로 정의한다.

주요 요약:

W/A/KV bitwidth을 IR에서 직접 표현

Mixed precision 기반 tile-level memory/latency 모델링 가능

bitwidth이 DMA/TE/VE/MemoryModel에 직접 영향

KV Cache와 LLM-centric 구조 완벽 지원

IR → TileGraph → CMDQ 전체 파이프라인에 quantization 정보가 일관되게 전파

이 스펙은 Mixed Precision NPU Simulator의 핵심 요소이며
향후 모든 quantization 관련 설계는 본 문서를 기준으로 확장해야 한다.
