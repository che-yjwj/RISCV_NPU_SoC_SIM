# Vector Engine Timing Specification  
**Path:** `docs/spec/timing/ve_timing_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Vector Engine Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU Simulator**에서 사용되는  
**Vector Engine(VE) Timing Model**의 정식 스펙을 정의한다.

Vector Engine은 아래 연산들을 담당하는 SIMD 기반 연산 유닛이다.

- LayerNorm  
- Softmax  
- GELU  
- Swish / Tanh / Sigmoid  
- RMSNorm  
- 기타 element-wise / reduction 기반 연산

VE는 TE처럼 대규모 GEMM을 처리하지는 않지만,  
**Transformer/LLM 구조에서 매우 중요한 연산 경로**를 담당하며  
특히 Softmax, LayerNorm, RMSNorm 등은  
시퀀스 길이에 따라 latency가 크게 변하는 특성을 가진다.

본 문서는 이러한 VE 연산의 tile-level latency 모델을  
정량적이고 일관된 방식으로 정의한다.

---

# 2. Vector Engine 개요 (Overview)

시뮬레이터 관점에서 Vector Engine은 아래처럼 단순화하여 정의한다.

- 입력: SPM 내에 저장된 activation tile  
- 출력: SPM 내에 저장되는 결과 tile  
- 내부 구조:
  - SIMD lanes 수(`lanes`)  
  - SFU(Special Function Unit) 레이턴시(예: exp, rsqrt)  
  - reduction pipeline latency  
  - pipeline depth, flush cost  

VE Timing Model은 **vector length**, **연산 종류**, **bitwidth**, **SFU 사용 여부** 등을 반영하여  
tile 단위 latency를 계산하도록 설계된다.

---

# 3. VE 관련 CMDQ Entry 필드 요약

VE timing 계산은 아래 CMDQ 엔트리 정보를 기반으로 한다.

| 필드명 | 설명 |
|--------|------|
| `ve_id` | 사용되는 Vector Engine index |
| `op_type` | LAYERNORM_TILE / SOFTMAX_TILE / GELU_TILE 등 |
| `length` | vector 길이 (예: hidden size = 4096) |
| `qbits_activation` | 연산에 사용되는 activation bitwidth |
| `spm_bank` | 입력 tile의 SPM bank |
| `spm_offset` | SPM offset |
| `spm_out_bank` | 출력 bank |
| `spm_out_offset` | 출력 offset |

---

# 4. 공통 Latency 모델 개요

VE 연산은 크게 다음 3단계를 포함한다.

1. **element-wise pass**  
2. **reduction pass** (필요한 경우)  
3. **post processing pass** (정규화, scaling, residual 등)

이를 다음과 같이 추상화하여 latency를 계산한다.

total_cycles = init_cycles
+ elementwise_cycles
+ reduction_cycles
+ finalize_cycles

perl
Copy code

각 항목은 연산 종류에 따라 달라지며, 아래 섹션에서 상세히 정의한다.

---

# 5. VE 성능 파라미터 (VE Performance Parameters)

아래 파라미터는 시뮬레이터 설정 파일에서 정의되며  
VE Timing Model의 핵심 구성 요소이다.

| 파라미터 | 설명 |
|----------|------|
| `lanes` | SIMD lane 개수 (ex. 64 lanes) |
| `ops_per_lane_factor` | lane 당 cycle당 처리 가능한 ops 수 |
| `sfu_latency_exp` | exp(x) SFU latency |
| `sfu_latency_rsqrt` | 1/sqrt(x) latency |
| `reduction_pipeline_latency` | reduction pass의 pipeline depth |
| `init_cycles` | VE 명령 초기 세팅 비용 |
| `finalize_cycles` | 결과 flush 비용 |
| `bitwidth_scale` | activation bitwidth에 따른 처리량 scaling factor |

SIMD 구조이므로 processing rate는 다음으로 표현된다.

ops_per_cycle_eff = lanes × ops_per_lane_factor × f_a(qbits)

yaml
Copy code

---

# 6. Bitwidth 기반 성능 스케일링

activation bitwidth(qbits_activation)는 VE 처리율에 영향을 줄 수 있다.

예시 scaling:

| qbits | scaling f_a |
|--------|-------------|
| 16     | 1.0         |
| 8      | 1.1         |
| 4      | 1.2         |

→ low-bit activation은 더 많은 요소를 한 cycle에 처리할 수 있다고 가정  
(정확한 scaling은 하드웨어 설정에 따라 결정 가능)

ops_per_cycle_eff = lanes × ops_per_lane_factor × f_a(qbits_activation)

yaml
Copy code

---

# 7. Element-wise Pass Latency

대부분의 VE 연산은 element-wise 또는 pointwise 계산을 포함한다.

## 7.1 Element-wise latency 공식

elementwise_cycles = ceil( length / ops_per_cycle_eff )

markdown
Copy code

예:

- length = 4096  
- ops_per_cycle_eff = 256  
→ elementwise_cycles = 16 cycles

## 7.2 SFU 기반 element-wise (exp, tanh 등)

Softmax, GELU 등은 SFU를 포함한 element-wise pipeline이 존재한다.

예:

- Softmax: exp(x)  
- GELU: erf(x) or tanh-based approx  
- Swish: sigmoid(x)

SFU latency를 고려하여 다음과 같이 계산한다.

elementwise_cycles_sfu =
elementwise_cycles

sfu_latency(op_type)

yaml
Copy code

- Softmax → exp → `sfu_latency_exp`  
- LayerNorm → rsqrt → `sfu_latency_rsqrt`

---

# 8. Reduction Pass Latency

LayerNorm, RMSNorm, Softmax는 reduction 연산을 포함한다.

## 8.1 Reduction 패턴

- LayerNorm: mean & variance  
- RMSNorm: variance only  
- Softmax: max, sum  

## 8.2 Reduction latency 공식

Reduction은 일반적으로 트리 기반 reduction pipeline으로 처리되므로 다음과 같이 추상화한다.

reduction_cycles
= reduction_pipeline_latency
+ ceil( log2(length) )

yaml
Copy code

`reduction_pipeline_latency`는 pipeline depth이며  
`ceil(log2(length))`는 tree reduction 단계 수에 해당한다.

예:

- length = 4096  
- log2(4096) = 12  
- reduction_pipeline_latency = 8  
→ reduction_cycles = 20 cycles

---

# 9. Finalization Pass Latency

Normalization, scaling, residual combine 등은  
element-wise 패스와 동일한 처리 모델을 사용할 수 있다.

예:

finalize_cycles = ceil( length / ops_per_cycle_eff )

Copy code

LayerNorm은 다음 형태가 된다.

LN total cycles =
init_cycles
+ (mean+var reduction)
+ (normalize pass)
+ finalize_cycles

yaml
Copy code

---

# 10. 연산 종류별 Timing 모델

아래는 주요 VE 연산의 latency 모델 정식 정의이다.

---

## 10.1 LayerNorm (LN)

LayerNorm tile latency는 다음 공식으로 계산한다.

LN_cycles =
init_cycles
+ reduction_cycles // mean/variance
+ elementwise_cycles_normalize // (x - mean) / sqrt(var + eps)
+ finalize_cycles

Copy code

정식 표현:

LN_cycles =
init_cycles

reduction_pipeline_latency

ceil(log2(length))

ceil(length / ops_per_cycle_eff)

finalize_cycles

yaml
Copy code

---

## 10.2 RMSNorm

LayerNorm과 유사하나 **variance만** 필요:

RMSNorm_cycles =
init_cycles

reduction_pipeline_latency // variance만

ceil(log2(length))

ceil(length / ops_per_cycle_eff)

finalize_cycles

yaml
Copy code

---

## 10.3 Softmax

Softmax tile 연산은 다음 단계를 거친다.

1. max reduction  
2. exp(x - max) element-wise (SFU)  
3. sum reduction  
4. final scaling

정식 latency:

Softmax_cycles =
init_cycles
+ (max reduction)
→ reduction_pipeline_latency + ceil(log2(length))
+ (exp pass)
→ ceil(length / ops_per_cycle_eff) + sfu_latency_exp
+ (sum reduction)
→ reduction_pipeline_latency + ceil(log2(length))
+ (normalize)
→ ceil(length / ops_per_cycle_eff)
+ finalize_cycles

yaml
Copy code

---

## 10.4 GELU

GELU(x)는 고비용 SFU(exp/tanh) 기반 모델이므로 다음과 같이 계산한다.

GELU_cycles =
init_cycles

ceil(length / ops_per_cycle_eff)

sfu_latency_gelu // (erf/tanh 기반)

finalize_cycles

yaml
Copy code

두 pass로 나누어도 되고, 하나의 SFU latency term으로 단순화해도 된다.

---

# 11. Multi-VE 환경에서의 타이밍 모델

NPU는 일반적으로 여러 개의 VE를 포함하며  
각 VE는 독립적으로 동작한다.

시뮬레이터는 아래 state를 유지한다.

```text
ve_state[ve_id]:
    busy_until_cycle
    current_op
운영 규칙
CMDQ의 VE_*_TILE 명령이 들어옴

deps_before 충족 시 issue 가능

해당 ve_id의 busy_until_cycle <= current_cycle이면 issue

issue 시:

start_cycle = current_cycle

end_cycle = current_cycle + VE_cycles

busy_until_cycle = end_cycle

TE timing과 유사하나, 연산 종류와 latency 모델이 다르다.

12. VE Timing Trace
TraceEngine은 VE tile 실행 시 아래 정보를 기록한다.

json
Copy code
{
  "engine": "VE",
  "id": 1,
  "cmdq_id": 73,
  "layer_id": "ln_3",
  "op_type": "LAYERNORM_TILE",
  "length": 4096,
  "qbits_activation": 8,
  "start_cycle": 123456,
  "end_cycle": 123504
}
이는 아래 분석에 활용된다.

VE utilization

LN/Softmax 병목 분석

sequence length 변화 시 latency scaling

multi-VE load balance

13. VE Timing 검증 규칙
시뮬레이터는 VE 명령 처리 전 다음을 검증한다.

length > 0

op_type가 지원되는 VE opcode인지

qbits_activation이 지원 bitwidth인지

SPM offset/bank가 유효한 범위인지

multi-VE 환경에서 ve_id가 범위를 벗어나지 않는지

검증 실패 시 CMDQ invalid 에러를 출력하고 시뮬레이션을 종료한다.

14. 확장성 (Extensibility)
VE timing spec은 다음 확장을 고려하고 있다.

rotary embedding → sin/cos 기반 SFU 연산 추가

log-softmax → extra reduction

fused LN + add + residual

fused attention score scaling

int1/int2 ultra-low-bit SIMD 경로

vector gather/scatter DMA와 결합된 hybrid VE ops

새 기능 추가 시 기존 공식의 구조를 유지하며
elementwise/reduction/SFU/pass 단위의 latency term을 더하는 방식으로 확장해야 한다.

15. 결론 (Summary)
ve_timing_spec.md는 NPU Simulator의 Vector Engine timing 모델을 정의하는 문서로서
Transformer/LLM 핵심 연산(LayerNorm, Softmax, GELU 등)의 정확한 tile-level latency 계산을 제공한다.

핵심 요약:

VE는 SIMD 기반 element-wise + reduction 기반 유닛

latency는
init + elementwise + reduction + sfu + finalize
구조로 구성

bitwidth 반영을 위해 f_a(qbits_activation) scaling 도입

multi-VE 환경에서 엔진별 busy timeline을 관리

TraceEngine과 결합하여 VE 타일의 성능 병목 분석 가능

이 스펙은 VE 동작 모델의 기준(reference)이며,
새로운 LLM 연산이나 bitwidth 스키마가 추가될 때
본 문서를 기반으로 확장해야 한다.

