# Bitwidth & Memory Mapping Specification  
**Path:** `docs/spec/quantization/bitwidth_memory_mapping.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Quantization / Memory Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU Simulator & Offline Compiler**에서 사용되는

- **bitwidth( qbits )**
- **dtype**
- **memory layout / alignment**
- **DRAM/SPM 상의 실제 byte 크기 및 주소 매핑 규칙**

을 공식적으로 정의한다.

이미 다음 문서에서 bitwidth가 언급되었으나:

- `docs/spec/ir/quantization_ir_extension.md`
- `docs/spec/ir/tensor_metadata_spec.md`
- `docs/spec/timing/dma_timing_spec.md`
- `docs/spec/timing/te_timing_spec.md`

본 문서는 그 중에서도 **“bitwidth → bytes → address”** 로 이어지는  
**정량적 규칙**을 집중적으로 다룬다.

---

# 2. 설계 목표 (Design Goals)

본 스펙의 목표는 다음과 같다.

1. **단일 규칙으로 모든 bitwidth에 대한 메모리 크기 계산**  
   - W/A/KV 각각 다른 qbits 사용  
   - int8 / int4 / int2 등 다양한 dtype 지원  
2. **DRAM / SPM / CMDQ / Timing 모델 간 일관성**  
   - DMA bytes, SPM capacity, TE/VE feed bandwidth를 하나의 규칙으로 연결  
3. **Packing / Alignment / Padding 명시**  
   - int4/int2처럼 sub-byte 단위 bitwidth에 대한 packing 정책 정의  
4. **Sim-friendly 단순 모델과, HW-leaning 확장 가능 모델의 공존**  

---

# 3. 기본 개념 (Basic Concepts)

### 3.1 qbits vs dtype

- **qbits**: 논리적인 양자화 bitwidth (2, 4, 8, …)  
- **dtype**: 실제 저장 타입 (fp32, fp16, int8, …)

본 스펙의 기본 가정:

- 초기 버전에서는 **qbits와 dtype의 bitwidth가 동일**한 케이스를 기본으로 한다.  
  - int8 → qbits=8  
  - int4 → qbits=4  
- int4/pack-int4처럼 “한 바이트에 여러 값 packing”은 **옵션**으로 다루고,  
  필요 시 확장 섹션에서 정의한다.

### 3.2 요소 수 vs bytes

- **num_elements**: 텐서 또는 타일에 포함된 논리적 요소 개수  
- **bitwidth(qbits)**: 한 요소당 bit 수  
- **bytes_total**: 실제 메모리에서의 총 바이트 수  

기본 공식:

```text
bits_total  = num_elements × qbits
bytes_total = ceil(bits_total / 8)
이 값이 DMA, SPM, DRAM, Bus 모델의 기본 입력이 된다.

4. bitwidth → bytes 변환 규칙
4.1 기본 공식
text
Copy code
bytes_total = ceil( num_elements × qbits / 8 )
예시
qbits = 8, num_elements = 4096

bits_total = 32,768

bytes_total = 4,096

qbits = 4, num_elements = 4096

bits_total = 16,384

bytes_total = 2,048

4.2 dtype와 qbits의 관계 (초기 버전)
초기 시뮬레이터에서는 다음을 기본 규칙으로 사용한다.

dtype	qbits 기본값	packing	설명
fp32	32	없음	4B per element
fp16	16	없음	2B per element
int8	8	없음	1B per element
int4	4	없음(옵션)	0.5B per element(논리)
int2	2	없음(옵션)	0.25B per element(논리)

int4/int2에 대해 “packed 형식”과 “unpacked 형식” 중
어느 쪽을 사용할지는 시뮬레이터 config로 제어한다.

5. Packing 모델 (옵션)
실제 하드웨어에서는 int4/2의 경우 bit-level packing을 사용하는 경우가 많다.
이를 반영하기 위한 packing factor를 정의한다.

5.1 Packing Factor 정의
pack_factor = 8 / qbits

예:

qbits=4 → pack_factor=2 (byte당 2 요소)

qbits=2 → pack_factor=4 (byte당 4 요소)

Packed bytes 계산
text
Copy code
bytes_total_packed = ceil( num_elements / pack_factor )
※ 실제 시스템에서 사용할지 여부는 config에 의해 결정
(예: use_packed_int4 = true/false).

5.2 초기 시뮬레이터 정책
초기 버전에서는 모델 단순화를 위해:

use_packed_int4 = false

use_packed_int2 = false

로 두고,
bytes_total = ceil( num_elements × qbits / 8 )
만 사용해도 충분하다.

packing을 활성화하면:

bytes_total 계산식이 packed 버전으로 변경

TE/VE timing 모델에서 macs_per_cycle_eff 계산에도 영향을 줄 수 있음

SPM capacity·bank conflict 모델에 더욱 현실적인 영향 반영 가능

6. Alignment & Padding 규칙
DMA, SPM, DRAM 접근은 특정 alignment를 요구한다.

6.1 Alignment 기본 규칙
Tensor Metadata의 alignment_bytes 필드 사용 (tensor_metadata_spec.md 참조).

DMA 경로에서:

text
Copy code
aligned_start = floor( dram_addr / alignment_bytes ) × alignment_bytes
aligned_end   = ceil( (dram_addr + bytes_total) / alignment_bytes ) × alignment_bytes
bytes_aligned = aligned_end - aligned_start
bytes_aligned는 실제 DRAM transaction에서 사용되는 크기

alignment에 의해 padding된 바이트는 유효 데이터가 아니지만,
bandwidth / latency에는 포함된다.

6.2 SPM alignment
SPM도 bank·port 측면에서 alignment 제약이 있을 수 있다.

spm_offset는 spm_alignment_bytes의 배수여야 한다.

초기 버전에서는 DRAM alignment만 명시적으로 다루고,
SPM alignment는 SPMAllocator가 보장하는 것으로 가정해도 된다.

7. DRAM / SPM 용량 및 점유 모델
7.1 DRAM 상 텐서 크기
TensorIR 기준 DRAM 상 텐서 크기:

text
Copy code
bytes_total_tensor = ceil( total_elements(tensor_shape) × qbits / 8 )
total_elements(tensor_shape)는 shape의 곱
(예: [B, T, H] → B×T×H)

7.2 Tile-level SPM 점유
TileGraph 단에서 각 타일은:

text
Copy code
bytes_tile = ceil( tile_num_elements × qbits / 8 )
SPMAllocator는:

각 bank의 용량 (spm_bank_size_bytes)

multi-bank 구조 (num_spm_banks)

를 고려하여 타일별 IFM/WGT/OFM/KV를 bank/offset에 매핑한다.

제약 조건:

text
Copy code
Σ bytes_tile_in_bank <= spm_bank_size_bytes
넘어갈 경우:

tile 크기를 줄이거나

tile 분할 방식 변경 필요 (TilingPlanner와 협업)

8. 역할별(bitwidth별) 메모리 특성 요약
8.1 Activation
보통 int8

qbits_activation = 8

DRAM traffic에 중간 정도 영향

SPM에 임시 저장 후 바로 TE/VE 입력으로 사용

8.2 Weight
2/4/8 bit 사용 가능 (초기 타겟: 4bit)

DRAM 용량 최적화 & bandwidth 절감의 핵심 타겟

Tile-based DMA로 SPM에 로드 후 반복 사용

8.3 KV Cache
일반적으로 4bit 또는 8bit

LLM에서 DRAM 상주, 각 token 추가 시 append

traffic 및 capacity 관점에서 가장 critical

KV bitwidth 조정에 따른 메모리 footprint 변화가
시뮬레이터에서 크게 드러나야 함

9. DMA Timing과의 연계
dma_timing_spec.md 에서 DMA latency는
bytes_aligned를 사용하여 결정된다.

프로세스:

IR / Tensor Metadata

qbits, shape, num_elements 존재

bytes_total 계산

text
Copy code
bytes_total = ceil(num_elements × qbits / 8)
alignment 적용

text
Copy code
bytes_aligned = apply_alignment(bytes_total, alignment_bytes)
DMA timing

num_bursts = ceil(bytes_aligned / bus_width)

latency_burst, latency_bw, contention_penalty 계산

bitwidth 변경은:

직접적으로 DMA bytes에 영향을 주고

간접적으로 NPU latency 및 bandwidth utilization에 영향을 준다.

10. TE / VE Timing과의 연계
TE/VE timing spec에서는 bitwidth가 다음에 사용된다.

TE: macs_per_cycle_eff = base × f_w(qbits_weight) × f_a(qbits_activation)

VE: ops_per_cycle_eff = lanes × ops_per_lane_factor × f_a(qbits_activation)

즉,

bitwidth는 compute throughput에도 영향을 주고

memory mapping과 결합하면 전체 성능 데이터가 나옴

이 문서는 bitwidth가 memory 측면에서 어떤 의미를 가지는지 정의하고 있고,
TE/VE timing spec은 bitwidth가 compute 측면에서 어떤 영향을 미치는지 정의한다.

11. 예시: End-to-end bitwidth → memory mapping
예시 조건
FFN weight tile:

num_elements = 4096 × 1024

qbits_weight = 4

alignment_bytes = 32

Activation tile:

num_elements = 4096

qbits_activation = 8

alignment_bytes = 32

11.1 Weight tile
text
Copy code
bits_total  = 4096 × 1024 × 4
bytes_total = ceil(bits_total / 8)
           = 2,097,152 bytes (약 2MB)

bytes_aligned
    = align_to(bytes_total, 32)
    = 2,097,152  (이미 32의 배수라고 가정)
11.2 Activation tile
text
Copy code
bits_total  = 4096 × 8
bytes_total = 4096
bytes_aligned = align_to(4096, 32) = 4096  (이미 32의 배수)
DMA, SPM, DRAM, TE/VE 모델 모두 이 결과를 공유한다.

12. Configuration Parameters
Bitwidth & Memory Mapping 동작은 config를 통해 커스터마이즈할 수 있다.

예: config/quantization_memory.yaml

yaml
Copy code
bitwidths:
  weight: [2, 4, 8]
  activation: [4, 8]
  kv: [4, 8]

packing:
  use_packed_int4: false
  use_packed_int2: false

alignment:
  default_alignment_bytes: 32
  weight_alignment_bytes: 64
  kv_alignment_bytes: 64

spm:
  bank_size_bytes: 262144
  num_banks: 8
13. Validation 규칙
시뮬레이터/컴파일러는 bitwidth & memory 관련 다음 사항을 검증해야 한다.

qbits가 지원 목록에 있는지 (예: {2,4,8,16,32})

bytes_total 계산 후 DRAM/ SPM 용량을 초과하지 않는지

alignment 규칙을 만족하는지

packing 사용 시 num_elements와 pack_factor 계산이 유효한지

KV cache 메모리가 모델 길이/bitwidth에 대해 충분한지

에러 시:

CMDQ 또는 IR validation 단계에서 에러 리포트

시뮬레이션 시작 전에 fail-fast

14. 확장성 (Extensibility)
향후 다음과 같은 확장을 고려한다.

fp8 / bfloat16 등 새로운 dtype 도입

run-length encoding / entropy coding 등 압축된 텐서 표현

sparsity-aware storage (CSR/CSC/block-sparse)

bank interleaving / channel interleaving

multi-rank HBM/DRAM 구성

새로운 특성을 도입할 때는
“bitwidth → bits_total → bytes_total → bytes_aligned”
의 기본 체인을 유지한 상태에서,

추가적인 scaling factor

추가적인 penalty term

별도의 storage_class-specific 규칙

형태로 확장하는 것을 원칙으로 한다.

15. 결론 (Summary)
bitwidth_memory_mapping.md는

“bitwidth가 실제 메모리에서 어떤 의미를 가지는가?”

에 대한 정량적 기준을 제공한다.

핵심 요약:

qbits와 num_elements로부터 bits_total과 bytes_total을 계산

alignment/padding을 통해 bytes_aligned를 도출

DRAM 용량, SPM capacity, DMA bandwidth, TE/VE feed 등에
모두 일관된 메모리 크기 정보를 제공

int4/int2 packing, alignment, KV cache 등의 특성을 포함하여
LLM-friendly한 bitwidth·memory 모델을 지원

이 스펙은 quantization / 메모리 모델 / timing 모델의
교차점에 위치하는 핵심 문서이며,
bitwidth 관련 정책 변경 시 항상 이 문서를 기준으로 업데이트해야 한다.