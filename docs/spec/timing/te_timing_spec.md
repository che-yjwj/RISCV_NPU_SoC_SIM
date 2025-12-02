# Tensor Engine Timing Specification  
**Path:** `docs/spec/timing/te_timing_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02  

---

# 1. 목적 (Purpose)

이 문서는 **NPU Simulator**에서 사용되는 **Tensor Engine(TE) Timing Model**을 정의한다.

Tensor Engine은 주로 다음 연산의 **tile-level compute latency**를 모델링한다.

- GEMM / MatMul (주력)  
- Conv (옵션, 향후 확장)  
- 기타 tensor 연산 (예: projection, pointwise matmul 등)

TE timing 모델은 다음을 목표로 한다.

1. **tile 단위 latency**를 명확한 수식으로 정의  
2. **bitwidth(W/A)** 및 엔진 구조(MAC/cycle, pipeline depth 등)를 반영  
3. **multi-TE 병렬 실행 모델**과 자연스럽게 결합  
4. **cycle-based simulator**에서 쉽게 구현 가능  
5. 실제 하드웨어와 ±10~15% 수준의 latency 차이를 목표로 하는,  
   **분석/튜닝용 시뮬레이터**에 적합한 정확도 제공  

---

# 2. Tensor Engine 개요 (Overview)

Tensor Engine(TE)는 NPU 내에서 **대규모 행렬 곱(MatMul/GEMM)** 을 담당하는 연산 유닛이다.

시뮬레이터 관점에서 TE는 다음과 같이 추상화된다.

- 입력: SPM에 존재하는 IFM / WGT 타일  
- 출력: SPM에 기록되는 OFM 타일  
- 타일 단위 연산: (M, K) × (K, N) → (M, N)  
- 내부 구조:  
  - `macs_per_cycle` (총 MAC 처리량)  
  - pipeline depth, init latency  
  - bitwidth에 따른 처리 효율 차이 반영 가능  

TE timing spec은 **GEMM 타일 하나의 latency를 계산하는 규칙**을 정의하고,  
multi-TE 환경에서의 병렬성을 고려한 **global timing model**과의 API를 제공한다.

---

# 3. TE 관련 CMDQ Entry 필드 요약

TE timing 계산의 입력은 CMDQ의 `TE_GEMM_TILE` 엔트리이다.  
(필드 상세 정의는 `cmdq_format_spec.md` 참조)

TE 관련 주요 필드는 다음과 같다.

| 필드명             | 설명 |
|-------------------|------|
| `te_id`           | 사용되는 Tensor Engine 인덱스 |
| `ifm_bank`        | SPM bank index (입력) |
| `ifm_offset`      | SPM offset (입력) |
| `wgt_bank`        | SPM bank index (weight) |
| `wgt_offset`      | SPM offset (weight) |
| `ofm_bank`        | SPM bank index (출력) |
| `ofm_offset`      | SPM offset (출력) |
| `m, n, k`         | GEMM tile 크기 (M×K · K×N) |
| `qbits_weight`    | weight bitwidth |
| `qbits_activation`| activation bitwidth |

시뮬레이터의 TE timing 모델은 위 필드를 기반으로  
**per-tile latency 및 TE busy time**을 계산한다.

---

# 4. GEMM Tile 연산량 계산

GEMM 타일의 총 MAC 연산량은 다음과 같이 정의한다.

```text
MACs_tile = M × N × K
```

여기서:

- M: output rows (tile 높이)  
- N: output columns (tile 너비)  
- K: reduction dimension (공통 inner dimension)  

예: M=64, N=128, K=256이면  
MACs_tile = 64 × 128 × 256

TE의 기본 timing 모델은 이 MACs_tile 값을
엔진의 처리 능력(macs_per_cycle)으로 나누어 latency를 추정하는 방식이다.

# 5. TE 성능 파라미터 (Performance Parameters)
TE timing 모델은 다음 하드웨어 파라미터에 의해 제어된다
(구체 값은 config 파일 또는 시뮬레이터 설정에서 제공).

파라미터 이름	설명  
macs_per_cycle_base	기준 bitwidth(예: W8A8)에서의 cycle당 MAC 처리량  
init_latency_cycles	파이프라인 warm-up, command decode, setup 비용  
finalize_latency_cycles	결과 write-back, flush 비용  
bitwidth_scale_weight	weight bitwidth에 따른 성능 scaling factor  
bitwidth_scale_activation	activation bitwidth에 따른 scaling factor  
max_parallel_tiles	TE 하나가 동시에 처리할 수 있는 타일 수 (보통 1)

bitwidth 스케일링은 다음과 같이 사용될 수 있다.

```text
macs_per_cycle_effective
    = macs_per_cycle_base
      × f_w(qbits_weight)
      × f_a(qbits_activation)
```
이때 f_w, f_a는 bitwidth에 따라 1 이상(가속) 또는 1 이하(감속)이 될 수 있는 scaling 함수이다.

# 6. Bitwidth 기반 성능 스케일링 모델
Mixed precision(W/A)를 반영하기 위해
weight/activation bitwidth에 따른 성능 스케일링을 정의한다.

6.1 스케일링 함수 정의
간단한 예시(초기 모델):

qbits	f_w(qbits_weight)
8	1.0
4	1.5
2	2.0

qbits	f_a(qbits_activation)
8	1.0
4	1.1

weight bitwidth가 줄어들수록
같은 로직에서 더 많은 weight를 병렬로 처리할 수 있다고 가정

activation bitwidth는 보통 weight만큼 큰 효과를 주지 않지만,
일부 구조에서는 read/write bandwidth에 영향을 줄 수 있음

6.2 Effective MAC/cycle

```text
macs_per_cycle_eff
    = macs_per_cycle_base
      × f_w(qbits_weight)
      × f_a(qbits_activation)
```

6.3 TE latency 기본 공식

```text
compute_cycles_raw = ceil( MACs_tile / macs_per_cycle_eff )
```

# 7. 파이프라인 및 오버헤드 모델
TE는 일반적으로 파이프라인 구조를 가지므로
tile 수행 시 다음과 같은 오버헤드를 고려한다.

명령 디코드 및 세팅: init_latency_cycles

파이프라인 flush 및 결과 commit: finalize_latency_cycles

최종 TE latency는 다음과 같이 계산한다.

```text
te_latency_tile
    = init_latency_cycles
      + compute_cycles_raw
      + finalize_latency_cycles
```
초기 버전에서는 파이프라인 숨김효과를 별도로 고려하지 않고
위와 같이 단순 합산 모델을 사용한다.
향후 다음과 같은 확장이 가능하다.

“steady state” tile 시 init/finalize를 일부 amortize

multi-tile pipeline overlap 모델 도입

# 8. SPM 접근 및 내부 대역폭 제약
TE는 SPM에서 IFM/WGT/OFM 데이터를 읽고/쓰며 동작한다.
DMA timing과 별도로, TE 내부에도 아래와 같은 제약이 존재할 수 있다.

SPM bank/port 대역폭

weight prefetch / double-buffered tile load

partial sum accumulation

초기 TE timing spec에서는 다음 단순 모델을 사용한다.

DMA에서 필요한 tile data가 이미 SPM에 존재한다고 가정

TE latency는 pure compute latency에 집중

데이터 부족/overlap 문제는 DMA timing + 스케줄링 측면에서 처리

SPM 내부 대역폭 제약은 TE의 macs_per_cycle_eff에 내재화

즉, macs_per_cycle_eff를 현실적인 값으로 설정하여 반영

이로써 TE timing spec은 compute 중심의 latency 모델에 집중한다.
SPM bank conflict 등의 메모리 이슈는
dma_timing_spec.md 및 MemoryModel 쪽에서 다룬다.

# 9. Multi-TE 환경에서의 타이밍 모델
NPU에는 일반적으로 여러 개의 TE가 존재한다.

num_te = 2, 4, 8, ...

각 te_id는 독립된 엔진으로 간주

CMDQ에서 te_id 필드는 어떤 TE에 tile을 할당할지 나타냄

시뮬레이터는 각 TE에 대해 아래 상태를 유지한다.

```text
te_state[te_id]:
    - busy_until_cycle
    - current_tile_info (optional)
```

9.1 TE tile issue 규칙
ControlFSM는 CMDQ의 TE_GEMM_TILE 엔트리를 본다.

해당 tile의 deps_before가 모두 완료되었는지 확인한다.

te_id에 해당하는 TE가
current_cycle >= busy_until_cycle 이면 issue 가능.

tile을 issue할 때:

start_cycle = current_cycle

end_cycle = current_cycle + te_latency_tile

te_state[te_id].busy_until_cycle = end_cycle

# 10. 예시: TE 타일 latency 계산
10.1 설정
macs_per_cycle_base = 4096 MACs/cycle

init_latency_cycles = 8 cycles

finalize_latency_cycles = 4 cycles

Tile 파라미터:

M = 64, N = 128, K = 256

qbits_weight = 4, qbits_activation = 8

스케일링 함수:

f_w(4) = 1.5

f_a(8) = 1.0

# 10.2 계산
MACs_tile = 64 × 128 × 256

macs_per_cycle_eff = 4096 × 1.5 × 1.0 = 6144

compute_cycles_raw = ceil(MACs_tile / 6144)

te_latency_tile = 8 + compute_cycles_raw + 4

이 te_latency_tile 값이 해당 타일의 busy 구간을 정의한다.

---

# 11. Throughput-bound vs Latency-bound 시나리오

TE는 `macs_per_cycle_eff`와 tile 크기에 따라 throughput-bound 또는 latency-bound처럼 보일 수 있다. 아래는 두 가지 extreme 예시이다.

## 11.1 Throughput-bound (큰 tile, 높은 utilization)

- `macs_per_cycle_base = 8192`  
- `f_w(4) = 2.0`, `f_a(8) = 1.0` → `macs_per_cycle_eff = 16384`  
- Tile: `M=256, N=256, K=256` → `MACs_tile = 256×256×256 ≈ 16.7M`

```text
compute_cycles_raw ≈ 16.7M / 16384 ≈ 1024 cycles
te_latency_tile ≈ init(8) + 1024 + finalize(4) = 1036 cycles
```

이 경우 init/finalize 오버헤드는 전체 latency에서 작은 비율을 차지하며, TE는 거의 최대 throughput으로 동작한다.

## 11.2 Latency-bound (작은 tile, 파이프라인 오버헤드 지배)

- 같은 TE 파라미터 (`macs_per_cycle_eff = 16384`)  
- Tile: `M=16, N=16, K=16` → `MACs_tile = 4096`

```text
compute_cycles_raw = ceil(4096 / 16384) = 1 cycle
te_latency_tile = init(8) + 1 + finalize(4) = 13 cycles
```

작은 tile에서는 실제 연산량보다 init/finalize가 latency를 지배하여 “latency-bound”에 가깝게 보인다. 타일링/스케줄러는 이 trade-off를 고려해 tile 크기와 병렬성을 조정해야 한다.

# 11. TE Timing과 Quantization의 관계
Quantization은 TE timing에 크게 두 가지 방식으로 영향 준다.

비트폭에 따른 연산 유닛 효율 변화

weight bitwidth가 줄어들수록 더 많은 weight를 한 cycle에 처리 가능

activation bitwidth도 부분적으로 영향

DMA Timing & SPM capacity에 간접 영향

low-bitweight → DMA bytes 감소 → feed 제공이 빨라짐

tile 크기/구성이 달라질 수 있음 (SPM에 더 많은 타일 저장 가능)

TE timing spec은 1번에 해당하는 연산 효율 부분에 집중하며,
2번은 dma_timing_spec.md 와 SPM/Tile 설계에서 처리한다.

# 12. TE Timing Trace
TraceEngine은 TE가 tile을 수행할 때 다음 정보를 기록한다.

```json
{
  "engine": "TE",
  "id": 0,
  "cmdq_id": 12,
  "layer_id": "ffn_2",
  "tile_shape": { "M": 64, "N": 128, "K": 256 },
  "qbits_weight": 4,
  "qbits_activation": 8,
  "start_cycle": 10000,
  "end_cycle": 10200,
  "macs": 2097152
}
```
이 정보는:

layer별 compute latency breakdown

multi-TE load balancing

bitwidth 변경 시 compute time 변화

Gantt Chart, utilization 그래프

등의 분석에 사용된다.

# 13. TE Timing 검증 규칙
시뮬레이터는 TE 명령 처리 시 다음을 검증해야 한다.

M, N, K > 0

macs_per_cycle_eff > 0

SPM에서 IFM/WGT/OFM 공간이 유효한 주소 범위 내에 존재하는지

(메모리 검사는 MemoryModel/Validator와 협업)

qbits_weight, qbits_activation가 지원 가능한 bitwidth인지

예: {2, 4, 8, 16}

오류 발생 시 CMDQ invalid 에러를 보고하고 시뮬레이션을 종료하는 것이 원칙이다.

# 14. 확장성 (Extensibility)
TE timing 모델은 다음과 같은 확장을 염두에 두고 설계되었다.

Conv 전용 타일 (TE_CONV_TILE)

K dimension이 다르게 해석되는 구조

sliding window / stride / padding 반영

Sparse GEMM

sparsity_ratio 필드 추가

MACs_tile를 MACs_tile × (1 - sparsity_ratio)로 조정

Low-rank / grouped matmul

Tile mapping 규칙 변경

여전히 MACs_tile 기반 모델 사용 가능

Pipeline overlap

init/finalize latency의 amortization

multi-tile pipeline scheduling 모델

Variable precision pipeline

int2/int1 등 ultra-low-bit에서 special path 사용

새로운 기능이 추가될 때는
기본 공식 구조를 유지하되, 스케일링 혹은 추가 term을 도입하는 방식으로 확장해야 한다.

# 15. 결론 (Summary)
te_timing_spec.md는 NPU Simulator에서의 Tensor Engine timing을 정의하는 핵심 문서이다.

핵심 요약:

GEMM tile의 연산량은 MACs_tile = M × N × K

TE의 처리 능력은 macs_per_cycle_eff로 표현되고,
bitwidth(W/A)에 따라 스케일링된다.

tile latency는
te_latency_tile = init + ceil(MACs_tile / macs_per_cycle_eff) + finalize

multi-TE 환경에서 각 TE는 독립적인 busy timeline을 가지며,
CMDQ의 te_id를 통해 타일이 분배된다.

Quantization, DMA, SPM 모델과 결합하여
전체 NPU 시뮬레이터의 compute 측 정확도를 결정한다.

본 스펙은 TE timing 모델의 기준(reference)이므로,
향후 TE 구조/성능이 변경되더라도
이 문서의 수식과 파라미터 정의를 우선적으로 갱신해야 한다.
