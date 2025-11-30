CMDQ Format Specification (Full Version)

Path: docs/spec/isa/cmdq_format_spec.md
Version: v1.0
Status: Stable Draft
<!-- status: complete -->
Owner: ISA / Compiler Architect
Last Updated: YYYY-MM-DD

1. 목적 (Purpose)

이 문서는 NPU Simulator & Offline Compiler에서 사용하는
Command Queue (CMDQ) 의 **포맷, 필드, 실행 의미(execution semantics)**를 정의한다.

CMDQ는 다음을 위해 설계된 NPU 전용 “실행 ISA” 이다.

오프라인 컴파일러가 생성한 정적 스케줄링 결과를 표현

NPU 내부 Control FSM이 순차적으로 fetch/execute할 수 있는 구조

DMA / Tensor Engine(TE) / Vector Engine(VE) / Sync / Control 연산을 통합

Mixed precision(multi-bitwidth) 및 multi-TE/VE를 모두 반영

Cycle-based simulator에서 timing/resource 모델과 직접 연동 가능

CMDQ 포맷은 컴파일러의 출력이자 시뮬레이터의 입력이므로,
이 문서에서 정의한 규칙이 시스템의 “단일 인터페이스 스펙” 역할을 한다.

2. 범위 (Scope)

포함 범위:

CMDQ 엔트리의 논리적 필드 정의 (opcode, operand, meta, sync, qbits 등)

JSON 기반 표현 스펙 (시뮬레이터/툴링 친화적 포맷)

실행 의미 (Control FSM이 어떻게 해석하는지)

확장 규칙 (새 opcode, 새 필드 추가 시 정책)

포함하지 않는 범위:

실제 하드웨어용 바이너리 인코딩 비트필드 (필요하다면 별도 문서에서 정의)

Host RISC-V ISA 디테일 (단, CMDQ launch CSR/MMIO 사용은 상위 아키텍처 문서에서 정의)

3. CMDQ 개념 및 실행 모델
3.1 CMDQ 개념

CMDQ(Command Queue)는 NPU가 실행할 명령들의 정적 시퀀스이다.

각 엔트리 = 1개의 NPU 명령 (DMA/TE/VE/SYNC/CONTROL 등)

Offline Compiler가 IR + Tiling + Scheduling 결과를 기반으로 생성

NPU 내부 Control FSM은 CMDQ를 순서대로 읽어 실행

3.2 실행 모델 요약

Host CPU가 CMDQ의 시작 주소/길이를 CSR/MMIO에 기록

NPU Control FSM이 CMDQ[0]부터 순차적으로 fetch

각 엔트리의 opcode에 따라 DMA/TE/VE job을 생성 또는 sync 처리

특정 엔트리(END)를 만나면 NPU 실행 종료

Control FSM은 **명령의 “순서 보장”**을 담당하고,
TE/VE/DMA 개별 엔진은 내부 queue/timing 모델에 의해 병렬 실행된다.

4. 전체 구조 (Top-Level Structure)

CMDQ는 엔트리 리스트로 구성된다.

{
  "cmdq": [
    { /* entry 0 */ },
    { /* entry 1 */ },
    ...
  ],
  "metadata": {
    "version": "1.0",
    "graph_name": "example_model",
    "generated_by": "offline_compiler",
    "created_at": "YYYY-MM-DD"
  }
}


엔트리들은 0-based index를 가지며, barrier/sync는 이 인덱스를 참조한다.

5. 공통 엔트리 스키마 (Common Entry Schema)

모든 CMDQ 엔트리는 다음 공통 필드 집합을 가진다.

{
  "opcode": "string",
  "id": 12,
  "layer_id": "ffn_2",
  "deps_before": [5, 6],
  "deps_after": [],
  "debug": {
    "comment": "optional",
    "source": "scheduler"
  }
}

5.1 필드 설명
필드명	타입	설명
opcode	string	명령 종류 (예: "DMA_LOAD_TILE", "TE_GEMM_TILE")
id	int	CMDQ 내 엔트리 인덱스(0-based). 명시하지 않으면 생성 시 부여 가능
layer_id	string/null	이 명령이 속하는 IR Layer ID. 프로파일/디버그에 사용
deps_before	int[]	이 엔트리가 실행되기 전에 완료되어야 할 CMDQ entry들의 id 목록 (barrier-like)
deps_after	int[]	이 엔트리가 완료된 후, 후속 의존성을 나타낼 때 사용 (선택)
debug	object	히스토리/주석 등 디버그용 메타데이터

주의:

deps_before는 스케줄링 결과이며, Control FSM은 이 조건을 만족하지 않는 한 엔트리를 issue하지 않는다.

단순한 글로벌 barrier는 별도의 BARRIER opcode로 정의 가능하지만,
보다 fine-grained한 타일 레벨 의존성은 deps_before를 주로 사용한다.

6. Opcode 카테고리 정의

CMDQ opcode는 아래 5개 카테고리로 나뉜다.

DMA 클래스: DRAM↔SPM 데이터 이동

TE 클래스: Tensor Engine 연산 (GEMM/Conv 등)

VE 클래스: Vector Engine 연산 (LN/Softmax/GELU 등)

SYNC/CONTROL 클래스: Barrier, NOP, END 등

LLM/특수 연산 클래스 (확장용): KV cache 관련 등

7. DMA 명령 포맷
7.1 DMA_LOAD_TILE

DRAM → SPM로 데이터 타일을 로드한다.

{
  "opcode": "DMA_LOAD_TILE",
  "id": 0,
  "layer_id": "attn_q",
  "tensor_role": "weight",              // weight / activation / kv
  "qbits": 4,                           // bitwidth used for this tile
  "dram_addr": 123456,
  "spm_bank": 0,
  "spm_offset": 0,
  "num_elements": 4096,
  "stride_bytes": null,                 // 옵션: 2D/ND load 시 사용
  "deps_before": [],
  "deps_after": []
}

7.2 DMA_STORE_TILE

SPM → DRAM로 데이터 타일을 저장한다.

{
  "opcode": "DMA_STORE_TILE",
  "id": 1,
  "layer_id": "attn_q",
  "tensor_role": "activation",
  "qbits": 8,
  "dram_addr": 654321,
  "spm_bank": 2,
  "spm_offset": 0,
  "num_elements": 2048,
  "stride_bytes": null,
  "deps_before": [10, 11],              // 예: TE 타일 완료 후 실행
  "deps_after": []
}

7.3 DMA 명령 필드 요약
필드명	타입	설명
tensor_role	string	"weight", "activation", "kv"
qbits	int	해당 타일의 bitwidth (예: 4, 8)
dram_addr	int	DRAM 기준 주소(바이트 단위)
spm_bank	int	SPM bank index
spm_offset	int	해당 bank 내 오프셋 (byte 단위 또는 요소 index)
num_elements	int	이 타일이 가지는 요소(element) 수
stride_bytes	int/null	0 또는 null이면 연속 데이터, 비연속이면 2D load/store로 해석

시뮬레이터의 DMA timing model은 num_elements와 qbits로부터
total_bytes → burst_transfers → dma_cycles를 계산한다.

8. TE 명령 포맷 (Tensor Engine)
8.1 TE_GEMM_TILE

GEMM/MatMul 타일을 TE에서 실행한다.

{
  "opcode": "TE_GEMM_TILE",
  "id": 10,
  "layer_id": "ffn_2",
  "te_id": 0,                      // TE 인덱스
  "ifm_bank": 0,
  "ifm_offset": 0,
  "wgt_bank": 1,
  "wgt_offset": 0,
  "ofm_bank": 2,
  "ofm_offset": 0,

  "m": 64,
  "n": 128,
  "k": 256,

  "qbits_weight": 4,
  "qbits_activation": 8,

  "deps_before": [2, 3],           // DMA_LOAD 완료 필요
  "deps_after": []
}

8.2 TE_CONV_TILE (옵션)

Conv → GEMM 변환을 사용하지 않고 직접 Conv 타일을 모사하려는 경우 사용한다.
필드 구조는 별도 확장 문서에서 정의할 수 있으며, 초기 버전에서는 GEMM 위주로 사용해도 된다.

8.3 TE 명령 필드 요약
필드명	타입	설명
te_id	int	사용할 Tensor Engine 인덱스 (0..N_te-1)
ifm_bank	int	SPM bank index for input feature map
ifm_offset	int	IFM base offset in bytes/elem
wgt_bank	int	SPM bank index for weights
wgt_offset	int	weight base offset
ofm_bank	int	SPM bank index for output
ofm_offset	int	output base offset
m, n, k	int	tile GEMM 크기
qbits_weight	int	weight bitwidth
qbits_activation	int	activation bitwidth

시뮬레이터는 이 정보를 바탕으로:

MAC ops = m * n * k

qbits_weight, qbits_activation에 따른 내부 처리 정책(예: compression overhead)을 적용 가능

TE별 busy/free timeline과 latency를 계산한다.

9. VE 명령 포맷 (Vector Engine)
9.1 VE_LAYERNORM_TILE

LayerNorm 타일을 VE에서 처리한다.

{
  "opcode": "VE_LAYERNORM_TILE",
  "id": 20,
  "layer_id": "ln_3",
  "ve_id": 1,

  "in_bank": 2,
  "in_offset": 0,
  "out_bank": 3,
  "out_offset": 0,

  "length": 1024,                  // 벡터 길이
  "qbits_activation": 8,

  "eps": 1e-5,

  "deps_before": [15],             // TE tile output 생성 이후
  "deps_after": []
}

9.2 VE_SOFTMAX_TILE

Softmax 타일:

{
  "opcode": "VE_SOFTMAX_TILE",
  "id": 21,
  "layer_id": "attn_softmax",
  "ve_id": 0,

  "in_bank": 4,
  "in_offset": 0,
  "out_bank": 4,
  "out_offset": 0,

  "length": 128,
  "qbits_activation": 8,

  "deps_before": [18],
  "deps_after": []
}

9.3 VE 명령 필드 요약
필드명	타입	설명
ve_id	int	사용할 Vector Engine 인덱스
in_bank	int	입력 SPM bank index
in_offset	int	입력 base offset
out_bank	int	출력 SPM bank index
out_offset	int	출력 base offset
length	int	연산 대상 벡터 길이
qbits_activation	int	activation bitwidth
eps	float	LayerNorm epsilon (적용되는 경우만)
10. SYNC / CONTROL 명령 포맷
10.1 BARRIER

여러 엔트리의 완료를 기다린 후 진행해야 할 경우 사용된다.
단, 실제 구현에서는 deps_before만으로 대부분 표현 가능하므로
BARRIER는 선택적 또는 high-level sync 용도로 사용한다.

{
  "opcode": "BARRIER",
  "id": 30,
  "layer_id": null,
  "wait_for": [10, 11, 20],   // 이 엔트리들이 모두 끝나야 barrier 통과
  "deps_before": [],
  "deps_after": []
}


실행 의미:

Control FSM은 wait_for에 포함된 CMDQ 엔트리들의 완료 상태를 확인

모두 완료될 때까지 BARRIER 다음 엔트리를 issue하지 않음

10.2 NOP

성능/정렬/디버그용으로 아무 것도 하지 않는 명령.

{
  "opcode": "NOP",
  "id": 99,
  "layer_id": null,
  "deps_before": [],
  "deps_after": []
}

10.3 END

CMDQ 실행 종료를 나타낸다.

{
  "opcode": "END",
  "id": 1000,
  "layer_id": null,
  "deps_before": [],
  "deps_after": []
}


Control FSM은 END를 만나면 NPU 실행을 종료하고 Host에게 완료 신호를 보낸다.

11. LLM / KV Cache 관련 명령 예시 (확장용)

LLM 워크로드를 명시적으로 표현하기 위한 확장 opcode 예시이다.

11.1 KV_CACHE_LOAD_TILE

KV Cache를 DRAM에서 SPM으로 로드.

{
  "opcode": "DMA_LOAD_TILE",        // reuse DMA opcode
  "id": 40,
  "layer_id": "attn_block_3",
  "tensor_role": "kv",
  "qbits": 4,
  "dram_addr": 900000,
  "spm_bank": 5,
  "spm_offset": 0,
  "num_elements": 8192,
  "deps_before": [],
  "deps_after": []
}


KV Cache는 tensor_role = "kv" + qbits_kv 로 구분된다.
별도의 opcode를 도입하지 않고 tensor_role 변경으로 처리하는 것이 기본 전략이다.

12. JSON 스키마 개념 (단순 개요)

정식 JSON Schema는 별도 파일로 관리할 수 있으나, 이 문서에서는 필수 제약만 요약한다.

opcode: enum of 지원 opcode 문자열

id: non-negative integer (0-based)

deps_before / deps_after: integer 배열, 각 값은 유효한 CMDQ id

te_id / ve_id: [0, N_te-1], [0, N_ve-1] 범위

qbits, qbits_weight, qbits_activation: {2, 4, 8, 16, 32} 등 제한된 set

주소/offset/num_elements는 모두 non-negative integer

13. 실행 시맨틱 (Execution Semantics)

Control FSM 관점에서 CMDQ 엔트리 하나의 처리 흐름은 다음과 같다.

opcode에 따라 엔진 타입(DMA/TE/VE/SYNC)을 판별

deps_before에 나열된 엔트리들이 모두 완료됐는지 확인

완료되지 않았다면 해당 엔트리 issue를 스킵하고 다음 엔트리로 넘어가거나,
“ready 큐”로 등록해 놓고 다시 polling

준비 완료 시, 해당 엔진의 큐에 job enqueue

엔진이 실제 work를 수행하면서 trace에 start/end cycle 기록

job 완료 시, 해당 CMDQ 엔트리의 완료 플래그 set

deps_after를 가진 후속 엔트리가 있다면, 그 의존성 해소에 사용 가능

시뮬레이터는 이를 기반으로 자원 사용률, 병목, latency를 산출한다.

14. 확장 규칙 (Extensibility Rules)

새로운 opcode 또는 필드를 추가할 때는 다음 원칙을 따른다.

기존 필드는 의미와 타입을 바꾸지 않는다.

새로운 opcode는 기존 enum에 추가하는 방식으로 확장

backward compatibility를 위해:

새로운 필드는 optional로 추가

구버전 CMDQ도 파싱 가능해야 함

하위 호환이 불가능한 변경이 필요한 경우:

metadata.version을 올리고

파서에서 버전별 분기 처리

15. 예제: 하나의 Layer에 대한 CMDQ 시퀀스

간단한 GEMM + LayerNorm 레이어에 대한 CMDQ 예시는 다음과 같다.

{
  "cmdq": [
    {
      "opcode": "DMA_LOAD_TILE",
      "id": 0,
      "layer_id": "ffn_2",
      "tensor_role": "activation",
      "qbits": 8,
      "dram_addr": 100000,
      "spm_bank": 0,
      "spm_offset": 0,
      "num_elements": 4096,
      "deps_before": [],
      "deps_after": []
    },
    {
      "opcode": "DMA_LOAD_TILE",
      "id": 1,
      "layer_id": "ffn_2",
      "tensor_role": "weight",
      "qbits": 4,
      "dram_addr": 200000,
      "spm_bank": 1,
      "spm_offset": 0,
      "num_elements": 16384,
      "deps_before": [],
      "deps_after": []
    },
    {
      "opcode": "TE_GEMM_TILE",
      "id": 2,
      "layer_id": "ffn_2",
      "te_id": 0,
      "ifm_bank": 0,
      "ifm_offset": 0,
      "wgt_bank": 1,
      "wgt_offset": 0,
      "ofm_bank": 2,
      "ofm_offset": 0,
      "m": 64,
      "n": 256,
      "k": 256,
      "qbits_weight": 4,
      "qbits_activation": 8,
      "deps_before": [0, 1],
      "deps_after": []
    },
    {
      "opcode": "VE_LAYERNORM_TILE",
      "id": 3,
      "layer_id": "ffn_2_ln",
      "ve_id": 0,
      "in_bank": 2,
      "in_offset": 0,
      "out_bank": 3,
      "out_offset": 0,
      "length": 256,
      "qbits_activation": 8,
      "eps": 1e-5,
      "deps_before": [2],
      "deps_after": []
    },
    {
      "opcode": "DMA_STORE_TILE",
      "id": 4,
      "layer_id": "ffn_2",
      "tensor_role": "activation",
      "qbits": 8,
      "dram_addr": 300000,
      "spm_bank": 3,
      "spm_offset": 0,
      "num_elements": 4096,
      "deps_before": [3],
      "deps_after": []
    },
    {
      "opcode": "END",
      "id": 5,
      "layer_id": null,
      "deps_before": [4],
      "deps_after": []
    }
  ]
}


이 한 시퀀스로:

activation/weight load

GEMM tile

LayerNorm

output store

종료까지 전체 flow를 표현할 수 있다.

16. 참조 문서

docs/overview/system_architecture.md

docs/spec/ir/npu_ir_spec.md

docs/spec/timing/dma_timing_spec.md

docs/spec/timing/te_timing_spec.md

docs/spec/timing/ve_timing_spec.md

docs/spec/quantization/bitwidth_memory_mapping.md

17. 결론

이 CMDQ Format Specification은:

컴파일러와 시뮬레이터 사이의 핵심 인터페이스를 정의하고

정적 스케줄링, mixed precision, multi-TE/VE, KV cache, LLM 워크로드 등
지금까지 정의한 모든 아키텍처 요구사항을 담을 수 있도록 설계되었다.