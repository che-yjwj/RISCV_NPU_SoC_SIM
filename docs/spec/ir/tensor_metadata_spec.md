# Tensor Metadata Specification  
**Path:** `docs/spec/ir/tensor_metadata_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** IR / Memory Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU IR(NPU Intermediate Representation)** 에서 사용하는  
**Tensor 메타데이터(Tensor Metadata)** 의 구조와 의미를 정의한다.

Tensor 메타데이터는 다음과 같은 역할을 수행한다.

- **IR → TileGraph → CMDQ → Simulator** 전 단계에서  
  모든 텐서의 **shape / dtype / layout / qbits / role / 메모리 특성**을 **일관된 방식으로 표현**  
- **SPM allocation, DMA transaction 계산, DRAM traffic 모델링, TE/VE 타이밍 모델**의 기초 데이터 제공  
- LLM 구조(특히 KV Cache), mixed precision, 다양한 레이어 타입 간 Tensor를 구분하고 관리

Tensor 메타데이터는 IR 내에서 **단일 Source of Truth**로 취급되며,  
다른 모듈(타일러, 스케줄러, 시뮬레이터)은 이 스펙을 반드시 준수해야 한다.

---

# 2. 설계 원칙 (Design Principles)

Tensor 메타데이터는 다음 원칙을 따른다.

### ✔ 2.1 구조적·단일화된 메타데이터  
모든 텐서(activation, weight, kv, intermediate 등)는 동일한 TensorIR 스키마를 따른다.  
Tensor 종류에 따라 `role`, `layout`, `qbits` 등이 달라질 뿐이다.

### ✔ 2.2 하드웨어 친화적 속성 포함  
- layout, alignment, bank mapping에 쓰일 정보  
- bitwidth 기반 capacity 계산에 필요한 정보  
- DRAM/Bus transaction 계산을 위한 요소 수, stride 등

### ✔ 2.3 상위 레이어부터 LLM까지 포괄  
- Conv/MLP/LN/GEMM 등 전통적 레이어  
- QKV projection, attention score, KV cache 등 LLM 레이어  

모두 표현 가능해야 한다.

### ✔ 2.4 IR / Quantization / Timing 스펙과 긴밀 연동  
본 문서에서 정의한 필드들은:

- `npu_ir_spec.md` (Graph/LayerIR)  
- `quantization_ir_extension.md`  
- `bitwidth_memory_mapping.md`  
- `dma_timing_spec.md`  

등과 연계되어 사용된다.

---

# 3. TensorIR Top-Level Schema

Tensor 메타데이터는 IR 내에서 다음과 같은 기본 스키마를 가진다.

```json
{
  "id": "string",
  "name": "string",
  "role": "activation | weight | kv | embedding | intermediate | output",
  "shape": [ "int", "int", "..." ],
  "dtype": "fp32 | fp16 | int8 | int4 | int2",
  "qbits": 8,
  "layout": "NCHW | NHWC | [B, T, H] | [B, H, T, D] | custom",
  "alignment_bytes": 16,
  "stride": null,
  "producer": "layer_id_or_null",
  "consumers": ["layer_id", "..."],
  "storage_class": "DRAM | SPM | CONST",
  "metadata": {
    "is_kv_head_split": false,
    "semantic": "q | k | v | logits | hidden | ...",
    "notes": ""
  }
}
각 필드는 아래에서 상세히 정의한다.

4. 필드 정의 (Field Definitions)
4.1 id (필수)
타입: string

의미: IR 전체에서 유일한 텐서 ID

규칙:

Graph 내에서 unique

LayerIR의 inputs/outputs는 반드시 TensorIR의 id를 참조

예: "hidden_3", "w_ffn1", "kv_cache_layer2_head0" 등

4.2 name
타입: string

의미: 디버그/로깅용 사람이 읽기 좋은 이름

규칙:

ONNX original 이름 또는 내부 규칙 기반

필수는 아니지만 가능하면 채워넣는 것을 권장

4.3 role
타입: string

허용 값 (초기 버전):

"activation"

"weight"

"kv"

"embedding"

"intermediate"

"output"

의미:

activation: 일반 layer 입력/출력, hidden state

weight: 학습된 파라미터(가중치, bias 포함)

kv: LLM KV cache 용 텐서

embedding: token embedding / positional embedding 등

intermediate: 내부 계층에서만 쓰이는 중간 텐서

output: 최종 모델 출력 (logits 등)

role은:

quantization 정책 (W/A/KV bit)

메모리 배치 (DRAM/CONST/캐시 전략)

분석/시각화 (어떤 텐서가 병목인지)

등을 판단하는 기준으로 사용된다.

4.4 shape
타입: int[]

의미: 텐서의 논리적 shape

예시:

[N, C, H, W]

[B, T, H]

[B, H, T, D]

중요:
shape는 논리적 단위이며, 실제 메모리 배치(layout)와는 분리된 개념이다.
layout에 따라 indexing 순서를 다르게 해석할 수 있다.

4.5 dtype
타입: string

허용 값 (초기 버전):

fp32, fp16

int8, int4, int2

의미:

메모리 혹은 연산에서 사용하는 저장 타입(Storage type)

실제 메모리 footprint 계산 시 dtype와 qbits 조합으로 해석

예:

모델 weight: dtype=int4, qbits=4

activation: dtype=int8, qbits=8

kv cache: dtype=int4, qbits=4

4.6 qbits
타입: int

의미: quantization bitwidth

자세한 정의는 quantization_ir_extension.md 및 bitwidth_memory_mapping.md 참조

일반적으로 dtype와 동일하나, 일부 내부 표현에서 다를 수 있다.

예:

dtype=int8, qbits=4: 4비트 양자화 값을 8비트 컨테이너에 packing 할 수도 있음(향후 확장용).

초기 버전에서는 dtype와 qbits를 동일하게 두고, 나중에 최적화 시 분리하는 전략 가능.

4.7 layout
타입: string

예시:

"NCHW", "NHWC"

"[B, T, H]"

"[B, H, T, D]"

"custom/..."

의미:

shape의 각 dimension이 실제로 어떤 의미를 갖는지 정의

TE/VE tile planner, SPM allocator, DMA pattern 등을 결정하는 데 사용

주요 패턴
CNN:

NCHW, NHWC

Transformer:

[B, T, H] → (batch, seq, hidden)

[B, H, T, D] → (batch, head, seq, head_dim) for Q/K/V

KV cache:

[B, H, T, D] with role="kv"

4.8 alignment_bytes
타입: int

의미: DRAM/버스/SPM에서 요구하는 정렬 단위(바이트 단위)

예:

16 / 32 / 64 bytes 등

사용처:

DMA address 정렬

SPM bank 시작 주소 정렬

bus transaction alignment

정렬 규칙은 bitwidth_memory_mapping.md 및 dma_timing_spec.md에서 상세히 다룸.

4.9 stride
타입: null 또는 int[]

의미:

메모리 상에서의 stride (byte 단위 or element 단위)

보통 dense layout에서는 null 또는 단순 계산 가능

패딩/서브샘플링/2D tile load 등에서 stride 정보가 필요할 수 있음

초기 버전에서는 null 또는 간단한 case만 지원해도 되며,
심화 버전에서 2D/ND stride를 명시적으로 지원할 수 있다.

4.10 producer
타입: string 또는 null

의미:

이 텐서를 생성한 LayerIR의 id

입력 텐서(모델 입력, 상수 등)의 경우 null

시뮬레이터에서 layer별 latency breakdown, dataflow 분석 등에 활용.

4.11 consumers
타입: string[]

의미:

이 텐서를 소비하는 LayerIR의 id 리스트

예:

Q/K/V projection에 들어가는 hidden state → 여러 레이어의 consumer로 사용 가능

Static scheduler는 producer/consumer 관계를 기반으로
데이터 의존성을 판단한다.

4.12 storage_class
타입: string

허용 값:

"DRAM": 일반 activation/kv 등이 DRAM 상에 상주

"SPM": 특정 텐서가 SPM에만 존재 (예: 타일화된 중간 결과)

"CONST": weight/embedding 등 변하지 않는 상수 텐서

storage_class는 다음에 영향:

DMA가 필요한지 여부 (DRAM↔SPM 이동)

시뮬레이터에서 DRAM traffic으로 계산할지 여부

KV cache/embedding 등 장기 상주 텐서의 관리 방식

4.13 metadata (확장 메타데이터)
타입: object (key-value)

예:

json
Copy code
"metadata": {
  "is_kv_head_split": true,
  "semantic": "k",      // q, k, v, logits, hidden, ...
  "notes": "layer_3 head_0 KV cache",
  "origin": "onnx://encoder.block.3.k_proj.weight"
}
semantic:

텐서의 의미를 추가적으로 설명하기 위한 태그

예: "q", "k", "v", "logits", "hidden", "residual", "embedding" 등

is_kv_head_split:

KV cache가 head dimension 기준으로 쪼개져 있는지 여부

tile planner가 head-parallelism을 사용할 때 활용 가능

이 영역은 run-time/분석 도구에서 자유롭게 확장 가능하나,
핵심 파이프라인(타일링/스케줄링)이 이 필드에 의존하지 않도록 설계하는 것이 원칙이다.

5. Tensor 종류별 메타데이터 예시
5.1 일반 MLP Weight 텐서
json
Copy code
{
  "id": "w_ffn1",
  "name": "ffn_block1_weight",
  "role": "weight",
  "shape": [4096, 1024],
  "dtype": "int4",
  "qbits": 4,
  "layout": "[N, K]",          // N: out_dim, K: in_dim
  "alignment_bytes": 32,
  "stride": null,
  "producer": null,
  "consumers": ["ffn_gemm1"],
  "storage_class": "CONST",
  "metadata": {
    "semantic": "weight",
    "notes": ""
  }
}
5.2 Hidden Activation 텐서 (Transformer 블록)
json
Copy code
{
  "id": "hidden_3",
  "name": "block3_hidden",
  "role": "activation",
  "shape": [1, 128, 4096],      // [B, T, H]
  "dtype": "int8",
  "qbits": 8,
  "layout": "[B, T, H]",
  "alignment_bytes": 32,
  "stride": null,
  "producer": "ffn_gemm2",
  "consumers": ["ln_3", "q_proj_3", "k_proj_3", "v_proj_3"],
  "storage_class": "DRAM",
  "metadata": {
    "semantic": "hidden",
    "notes": ""
  }
}
5.3 KV Cache 텐서
json
Copy code
{
  "id": "kv_cache_layer3_head0",
  "name": "kv_cache.l3.h0",
  "role": "kv",
  "shape": [1, 1, 128, 64],     // [B, H(=1), T, D]
  "dtype": "int4",
  "qbits": 4,
  "layout": "[B, H, T, D]",
  "alignment_bytes": 32,
  "stride": null,
  "producer": "kv_update_layer3_head0",
  "consumers": ["attn_scores_layer3_head0", "kv_update_layer3_head0"],
  "storage_class": "DRAM",
  "metadata": {
    "semantic": "kv",
    "is_kv_head_split": true,
    "notes": "KV cache for layer 3, head 0"
  }
}
5.4 Embedding 텐서
json
Copy code
{
  "id": "tok_embedding",
  "name": "token_embedding_table",
  "role": "embedding",
  "shape": [32000, 4096],       // vocab_size, hidden_dim
  "dtype": "fp16",
  "qbits": 16,
  "layout": "[V, H]",
  "alignment_bytes": 64,
  "stride": null,
  "producer": null,
  "consumers": ["embedding_lookup"],
  "storage_class": "CONST",
  "metadata": {
    "semantic": "embedding",
    "notes": "shared token embedding"
  }
}
6. Tensor Metadata와 다른 스펙 간 관계
Tensor 메타데이터는 다음 스펙들과 밀접하게 연동된다.

6.1 npu_ir_spec.md
LayerIR의 inputs / outputs는 TensorIR의 id를 참조

IR에서 layer-level shape / qbits / role 등은 TensorIR와 반드시 일관돼야 함

6.2 quantization_ir_extension.md
qbits 필드는 quantization extension에서 정의한 정책을 기반으로 설정

LayerIR-level qbits 필드와 TensorIR-level qbits 필드는 서로 상응해야 함

bitwidth 변화 실험 시 TensorIR의 qbits 변경이 DMA/Timing/Trace에 모두 반영

6.3 bitwidth_memory_mapping.md
shape + dtype + qbits + alignment_bytes를 조합하여
total bytes, transaction 수, burst 수 등을 계산

DMA Timing, SPM capacity, bandwidth 모델에 직접 사용됨

6.4 dma_timing_spec.md, te_timing_spec.md, ve_timing_spec.md
DMA: Tensor의 요소 수 및 qbits → total bytes → latency

TE/VE: qbits를 이용한 internal compute 패턴(예: packed int4)의 latency 모델링에 활용 가능

7. 정렬(Alignment) 및 패딩(Padding) 규칙 개요
정확한 규칙은 bitwidth_memory_mapping.md에서 정의되지만,
Tensor Metadata에서 alignment 개념은 다음과 같이 사용된다.

alignment_bytes는 DRAM 주소 정렬에 사용

tile-level DMA load/store 시:

시작 주소가 alignment_bytes의 배수인지 확인

필요시 padding 영역이 발생할 수 있음

SPMAllocator는 bank/offset 계산 시 alignment를 고려

패딩된 부분의 실제 수치는 시뮬레이터가 고려하지 않고,
단지 bytes/latency 측면에서만 영향을 준다고 가정할 수 있다.

8. Validation 규칙 (사전 검증)
Tensor 메타데이터는 IR 생성/로딩 시 다음을 검사하는 것이 바람직하다.

id uniqueness

shape와 layout의 consistency

qbits가 지원 범위(예: {2,4,8,16}) 내에 있는지

role과 storage_class 조합이 타당한지

weight/embedding → CONST가 일반적

activation/kv → DRAM이 일반적

producer/consumers 관계가 실제 Graph와 일치하는지

해당 검증 로직은 별도의 validator 모듈에서 구현할 수 있다.

9. 확장성 (Extensibility)
Tensor Metadata 스펙은 다음과 같은 확장을 염두에 두고 설계되었다.

새로운 role: "mask", "attention_bias", "rotary_factor" 등

새로운 dtype/qbits: fp8, bfloat16, int1 등

sparsity 관련 필드: sparsity pattern, block size 등

압축(compression) 정보: RLE/entropy coding에 대한 메타데이터

이러한 확장은 기존 필드의 의미를 변경하지 않고
새로운 필드를 추가하는 방식으로 진행해야 한다.

10. 결론 (Summary)
tensor_metadata_spec.md는 NPU IR에서 사용되는 모든 텐서에 대해:

shape / dtype / layout / role / qbits / storage / alignment
을 일관된 방식으로 정의하는 핵심 스펙 문서이다.

이 메타데이터는:

IR Graph의 구조적 일관성을 보장하고

Tiling/SPM allocation/Scheduling의 기반 정보를 제공하며

DMA/Timing/Trace/Visualization에 이르는 모든 단계에서 사용된다.

따라서, Tensor 메타데이터 스펙은
**NPU 시뮬레이터와 오프라인 컴파일러 전체의 공통 언어(common language)**로서
지속적으로 유지·관리되어야 한다.