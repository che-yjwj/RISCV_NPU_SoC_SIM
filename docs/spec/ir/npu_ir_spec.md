NPU IR Specification (Full Version)

Version: v1.0
Status: Stable Draft
<!-- status: complete -->
Owner: System Architect
Last Updated: YYYY-MM-DD

1. 목적 (Purpose)

본 문서는 NPU Simulator & Offline Compiler에서 사용되는 내부 IR(Intermediate Representation)인
NPU IR의 구조, 데이터 모델, 노드/텐서 스키마, quantization 표현, tile 변환 규칙을 규정한다.

이 IR은 다음의 목적을 충족하기 위해 설계되었다.

ONNX 모델을 손실 없이 내부 표현으로 변환

정적 스케줄링 및 타일링을 위한 구조화된 그래프 제공

Mixed-precision Quantization(W/A/KV bitwidth) 정의

TileGraph 생성 및 CMDQ serialization을 위한 기반 정보 제공

TE/VE/DMA 스케줄링 및 자원 모델링과 연동 가능

LLM-Friendly 구조(KV Cache, attention ops) 반영

이 IR 스펙은 오프라인 컴파일러 전체의 단일 소스 오브 트루스이며,
타일링/스케줄링/CMDQ 생성 로직은 모두 본 문서에서 정의한 구조를 준수해야 한다.

2. 설계 철학 (Design Principles)

NPU IR은 다음의 설계 철학을 따른다.

✔ 2.1 Layer-level 중심 (Graph IR)

운영 단위는 Layer이며, Transformer/Conv/MLP/LN 등 연산 단위를 그대로 반영한다.

✔ 2.2 Quantization-aware

W/A/KV 각기 다른 bitwidth를 갖는 mixed-precision quantization을 표현 가능해야 한다.

✔ 2.3 Tile-friendly

TileGraph가 쉽게 생성되도록 shape/layout 정보가 명확히 정의되어야 한다.

✔ 2.4 CMDQ-friendly

각 IR 노드는 CMDQ 명령 스트림으로 1:多 tile 연산으로 변환될 수 있어야 한다.

✔ 2.5 LLM-friendly 구조

Q/K/V projection

Multi-head attention

RMSNorm, LayerNorm

KV Cache (증분 업데이트)

을 직접 표현할 수 있어야 한다.

3. IR Top-Level Structure

NPU IR은 아래 3개의 주요 데이터 구조로 구성된다.

NPU_IR
 ├── Graph
 │     ├── nodes[]  → LayerIR
 │     └── edges[]  → Tensor references
 ├── TensorTable    → TensorIR
 └── QConfig        → Quantization policy

4. Graph IR 구조 (Layer-Level IR)

Graph는 Directed Acyclic Graph(DAG)로 표현되며,
노드 하나가 하나의 Layer를 의미한다.

4.1 Graph Schema
{
  "graph": {
    "nodes": [ ... ],
    "inputs": [ ... ],
    "outputs": [ ... ],
    "metadata": {
      "model_name": "string",
      "opset_version": "int"
    }
  }
}

5. LayerIR 구조

LayerIR은 IR에서 가장 중요한 단위이며,
각 LayerIR은 ONNX의 노드보다 더 구조적이며 tile/schedule-friendly하게 변환된다.

5.1 LayerIR 공통 스키마
{
  "id": "string",
  "op_type": "string",
  "inputs": ["tensor_id", ...],
  "outputs": ["tensor_id", ...],
  "attributes": {},
  "shape": {}, 
  "qbits_weight": 8,
  "qbits_activation": 8,
  "qbits_kv": null,
  "metadata": {
    "layer_name": "string",
    "subgraph": null
  }
}

설명

id: 그래프 내 유일 ID

op_type: GEMM / CONV / LN / QKV_PROJ / SOFTMAX 등

inputs/outputs: TensorIR ID 리스트

attributes: kernel, stride, axis 등

shape: output tensor shape

qbits_weight / activation / kv: quantization bitwidth

metadata: 디버그/추적용 이름

5.2 대표 연산별 LayerIR 예시
• GEMM / MatMul
{
  "id": "gemm_12",
  "op_type": "GEMM",
  "inputs": ["x_11", "w_12"],
  "outputs": ["y_12"],
  "shape": { "M": 1024, "N": 4096, "K": 1024 },
  "qbits_weight": 4,
  "qbits_activation": 8
}

• LayerNorm
{
  "id": "ln_4",
  "op_type": "LAYER_NORM",
  "inputs": ["x_4", "gamma_4", "beta_4"],
  "outputs": ["y_4"],
  "attributes": { "eps": 1e-5 },
  "qbits_activation": 8
}

• Self-Attention (Q/K/V Projection)
{
  "id": "qkv_2",
  "op_type": "QKV_PROJ",
  "inputs": ["hidden_1", "w_q", "w_k", "w_v"],
  "outputs": ["q_2", "k_2", "v_2"],
  "shape": {
    "batch": 1,
    "seq": 128,
    "heads": 8,
    "dim": 64
  },
  "qbits_weight": 4,
  "qbits_activation": 8
}

• KV Cache Update (LLM)
{
  "id": "kv_update_2",
  "op_type": "KV_UPDATE",
  "inputs": ["k_2", "v_2", "kv_cache_base"],
  "outputs": ["kv_cache_out"],
  "shape": { "seq_new": 1, "heads": 8, "dim": 64 },
  "qbits_kv": 4
}


KV Cache는 일반 activation과 bitwidth가 다르며, 메모리 모델과 직접 연결됨.

6. Tensor IR 구조 (Tensor-Level IR)

TensorTable은 모든 텐서 메타데이터를 갖는다.

6.1 TensorIR 스키마
{
  "id": "string",
  "shape": [ ... ],
  "dtype": "fp32 | int8 | int4 | int2",
  "qbits": null | 8 | 4 | 2,
  "role": "activation | weight | kv | intermediate",
  "layout": "NCHW | NHWC | NT(H) | [B, T, H]",
  "producer": "layer_id",
  "consumers": ["layer_id", ...]
}

6.2 Tensor 예시
• Weight Tensor
{
  "id": "w_12",
  "dtype": "int4",
  "qbits": 4,
  "role": "weight",
  "shape": [4096, 1024]
}

• Activation Tensor
{
  "id": "hidden_3",
  "dtype": "int8",
  "qbits": 8,
  "role": "activation",
  "shape": [1, 128, 4096]
}

• KV cache tensor
{
  "id": "kv_cache_head3",
  "dtype": "int4",
  "qbits": 4,
  "role": "kv",
  "shape": [1, 128, 64]
}

7. Quantization 정보 관리 (QConfig Integration)

Quantization 정책은 별도 스펙(QConfig)에 정의되며, IR에는 annotation만 삽입한다.

7.1 Layer-level bit annotation 규칙
Field	의미
qbits_weight	weight 텐서 bitwidth
qbits_activation	activation 텐서 bitwidth
qbits_kv	KV 전용 bitwidth
기본 규칙

weight/activation/KV 각각 독립 설정

qbits_kv는 attention block에서만 사용

int4/8/16/fp16 등 확장 가능

7.2 IR Annotation Example
{
  "id": "proj_q",
  "op_type": "GEMM",
  "qbits_weight": 4,
  "qbits_activation": 8,
  "qbits_kv": null
}

8. Shape / Layout 규칙

TE/VE/tile planner에 맞게 정규화된 layout을 사용한다.

8.1 Layout 규칙

GEMM → (M, K) × (K, N)

Attention

Q/K/V shape: (Batch, Seq, Heads, Dim)

KV Cache: (Batch, Heads, Seq, Dim)

8.2 Rank normalization

모든 텐서는 최소 2D~4D의 정규화된 형태를 갖도록 변환된다.

9. IR → TileGraph 변환 규칙

LayerIR은 tile 단위로 분해되어 TileGraph를 형성한다.

9.1 Tile 구조

Tile은 다음 정보를 갖는다.

TileNode:
  - parent_layer_id
  - tile_shape
  - te_id / ve_id (optional)
  - qbits (W/A/KV)
  - spm_allocation

9.2 변환 규칙

LayerIR의 shape 기반으로 tile 크기 결정

SPM 용량으로 tile 크기 제약

TE/VE 개수에 따라 tile 분배

각 tile은 CMDQ에서 TE_TILE/VE_TILE로 매핑

10. IR → CMDQ 변환 규칙

각 LayerIR은 다음의 CMDQ 시퀀스로 변환된다.

DMA_LOAD(ifm tiles)
DMA_LOAD(weight tiles)
TE_GEMM_TILE / VE_TILE (tile별 실행)
DMA_STORE(ofm tiles)

10.1 예시: GEMM Layer

IR:

{
  "op_type": "GEMM",
  "shape": { "M": 2048, "N": 4096, "K": 2048 }
}


CMDQ tile 변환 예시:

tile0: TE0_GEMM_TILE
tile1: TE1_GEMM_TILE
tile2: TE0_GEMM_TILE
tile3: TE1_GEMM_TILE


TE parallelism 반영.

11. LLM Friendly IR 확장

NPU IR은 다음 LLM 관련 연산을 직접 표현할 수 있도록 설계되었다.

Q/K/V projection

attention score matmul

softmax

attention output matmul

KV cache update

layernorm / rmsnorm

KV Cache는 별도 규칙 적용

qbits_kv 필수

append/concat-based seq 증가 표현

타일링은 seq 축을 기준으로 수행

12. IR 버전 관리 (Versioning)

IR에는 아래 메타데이터가 포함된다.

"ir_version": "1.0",
"spec_version": "1.0",
"created_by": "compiler",
"created_at": "YYYY-MM-DD"


변경 정책:

뒤로 호환 유지(backward-compatible) 가능하도록 설계

opcode 확장과 함께 IR 필드 확장 가능

13. 참조 문서

docs/spec/ir/tensor_metadata_spec.md

docs/spec/quantization/quantization_model_overview.md

docs/spec/isa/cmdq_format_spec.md

docs/spec/timing/*

docs/overview/system_architecture.md

14. 결론

본 NPU IR Specification은
OFFLINE COMPILER의 중심 데이터 구조이며,

그래프 표현

mixed precision quantization

tile-friendly 구조

CMDQ 변환 용이성

LLM-friendly 확장성

을 모두 만족하도록 설계된 핵심 스펙 문서이다.