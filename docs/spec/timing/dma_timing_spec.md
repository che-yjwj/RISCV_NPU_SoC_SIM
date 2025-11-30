# DMA Timing Specification  
**Path:** `docs/spec/timing/dma_timing_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Memory / Bus / DMA Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU Simulator의 DMAEngine timing model**을 정의한다.  

DMAEngine은 DRAM ↔ SPM 간 데이터 전송을 담당하며,  
cycle-based 시뮬레이터에서 **정확한 latency, bandwidth, contention 모델**을 제공하기 위해  
다음과 같은 요소들을 계산해야 한다.

- bitwidth 기반 실제 전송 bytes  
- DRAM burst / bus width / channel 개수  
- bank conflict / alignment penalty  
- multi-engine 병렬 동작 시 contention  
- DMA load / store / prefetch의 차이  
- tile-level granularity에 최적화된 latency 모델 제공  

본 스펙은 위 요구들을 충족하도록 **DMA Timing 규칙**을 정의한다.

---

# 2. DMAEngine Overview

DMAEngine은 다음과 같은 구조로 동작한다.

CMDQ → DMAEngine → DRAM/Bus Model → SPM

DMA LOAD/STORE 명령의 timing은 다음 요소로 결정된다:

```text
latency = address_alignment_penalty
        + burst_transfer_latency
        + bus_contention_penalty
        + sram_conflict_penalty
```

각 요소는 이후 섹션에서 공식적으로 정의한다.

---

# 3. DMA CMDQ Entry 필드 요약

DMA timing 계산은 CMDQ의 다음 필드를 기반으로 한다.

필드 상세는 `cmdq_format_spec.md` 참조.

| 필드           | 설명 |
|----------------|------|
| `tensor_role`  | activation / weight / kv / embedding |
| `qbits`        | bitwidth, bytes 계산에 직접 사용 |
| `dram_addr`    | DRAM 시작 주소 |
| `dram_stride`  | optional, 2D DMA 경우 |
| `spm_bank`     | SPM bank index |
| `spm_offset`   | SPM 내 byte offset |
| `num_elements` | 전송할 tensor 요소 수 |
| `shape`        | tile의 1D/2D 범위 |
| `dma_type`     | LOAD / STORE / PREFETCH |

---

# 4. Bytes 계산 규칙

DMAEngine은 bitwidth 기반으로 실제 전송 bytes를 계산한다.

```text
bytes = ceil((num_elements * qbits) / 8)
```

### 4.1 Alignment 적용

DMA는 DRAM access alignment에 영향을 받는다.

```text
aligned_start = align(dram_addr, alignment_bytes)
aligned_end   = align(dram_addr + bytes, alignment_bytes)
bytes_aligned = aligned_end - aligned_start
```

alignment_bytes는 Tensor Metadata에서 제공한다  
(`tensor_metadata_spec.md` 참고).

### 4.2 Weight / KV cache / Activation별 bitwidth 차이

| 역할 | typical qbits | bytes 영향 |
|------|---------------|------------|
| activation | 8 | 일반 DMA |
| weight | 2/4 | 매우 작은 bytes → 높은 tile parallelism |
| kv cache | 4 | LLM에서 DRAM bottleneck의 핵심 요소 |

low-bitweight 텐서의 bytes 감소는 DMA latency에 직접 반영된다.

---

# 5. DRAM Burst 모델

DMAEngine은 DRAM burst 기반 latency 모델을 사용한다.

### Key parameters

| 파라미터 | 설명 |
|----------|------|
| `bus_width_bytes` | 예: 32 bytes |
| `dram_burst_length` | 예: 16 bursts |
| `peak_bw_bytes_per_cycle` | DRAM+Bus 조합의 peak bandwidth |

### Burst 수 계산

```text
num_bursts = ceil(bytes_aligned / bus_width_bytes)
```

### DRAM burst latency

```text
latency_burst = num_bursts * dram_burst_cycles
```

`dram_burst_cycles`는 DRAM timing parameter  
(tRCD/tCL/tRP 등을 추상화한 평균 latency)로 정의된다.

---

# 6. Effective Bandwidth 모델

버스트 기반 모델 외에도 비율 기반 latency 모델을 함께 사용한다.

```text
latency_bw = bytes_aligned / peak_bw_bytes_per_cycle
```

실제 DMA latency는 두 모델의 합 또는 max 값을 사용한다.

### 옵션 A: Conservative (max)

```text
dma_latency_raw = max(latency_burst, latency_bw)
```

### 옵션 B: Hybrid (합산)

```text
dma_latency_raw = latency_burst + latency_bw
```

초기 버전에서는 A(max) 방식을 사용한다.  
(모던 NPU 문헌에서 conservative 모델이 일반적)

---

# 7. Bus Contention 모델

Multi-TE/VE 동작 시 여러 DMA 요청이 동시에 발생할 수 있으므로  
Bus contention 모델이 포함되어야 한다.

### 7.1 Bandwidth 공유 방식

두 가지 방식을 지원:

#### 방식 1: Shared Bandwidth with Slowdown

동시 active DMA 요청 수 = `N`  
→ effective bandwidth = `peak_bw_bytes_per_cycle / N`

#### 방식 2: FIFO Queue (Queue-level Scheduling)

- DMAEngine은 글로벌 큐에서 DRAM 접근을 1개씩만 허용  
- 각 요청은 DRAM 접근이 끝날 때까지 독점  
- 간단하지만 정확도가 낮음

초기 버전에서는 방식 1(shared bandwidth)을 채택한다.

### 7.2 Contention penalty 공식

```text
dma_latency_cont   = dma_latency_raw * contention_factor
contention_factor  = active_dma_count
```

즉, 두 DMA가 동시에 active면  
latency는 대략 2배 증가.

---

# 8. SPM Side Timing (Bank Conflict Model)

DMA는 DRAM뿐 아니라 SPM에도 영향을 준다.

SPM은 banked 구조이며, 다음 규칙을 따른다:

- element index → bank index = `(addr / bank_width) % num_banks`
- 특정 cycle에 한 bank에서 하나의 request만 처리 가능  
- DMA LOAD → SPM write  
- DMA STORE → SPM read  

### 8.1 Bank conflict penalty

```text
spm_conflict_penalty = num_conflicts * spm_conflict_cycles
```

`num_conflicts`는 address stride, tile shape, qbits 크기로부터 추론 가능.

### 8.2 DMA latency에 결합

```text
dma_latency_final = dma_latency_cont + spm_conflict_penalty
```

---

# 9. PREFETCH 모델 (옵션)

PREFETCH DMA는 실제 실행과 decoupled 되며  
ControlFSM이 issue만 하고, 언제든지 SPM에 놓을 수 있도록 설계되었다.

### Prefetch 규칙

1. Prefetch는 SPM 공간이 비어있을 때만 가능  
2. Prefetch latency는 일반 DMA latency와 동일  
3. Prefetch가 너무 일찍 끝나면 **hold state**에서 기다려야 한다  
4. Prefetch tile은 TE tile 실행 전에 반드시 완료되어야 한다

Prefetch에 대한 세부 스케줄링은  
Static Scheduler가 결정하고  
DMAEngine은 timing만 계산한다.

---

# 10. 타일 단위 DMA 예시

### 입력

```json
{
  "opcode": "DMA_LOAD_TILE",
  "tensor_role": "kv",
  "qbits": 4,
  "dram_addr": 12000,
  "num_elements": 4096,
  "spm_bank": 2,
  "spm_offset": 1024
}
```

계산 과정

```text
bytes = 4096 * 4 / 8 = 2048 bytes
```

alignment (32B) → 2048 → 2048 bytes

num_bursts               = ceil(2048 / 32) = 64
DRAM burst latency       = 64 * dram_burst_cycles
bandwidth-limited latency = 2048 / peak_bw
contention_factor        = active_dma_count

최종 latency:

```text
dma_latency_final =
    max(burst_latency, bw_latency)
  * contention_factor
  + spm_conflict_penalty
```

# 11. Cycle-based 동작 모델
DMAEngine은 시뮬레이터의 global cycle loop에서 다음과 같이 동작한다.

```text
for cycle in global_cycle:
    if dma_queue not empty:
        current_dma.progress(cycle)
    if dma finished:
        emit completion event
```
DMA 요청은 아래 상태를 가진다.

- Ready  
- Allocated  
- Transferring  
- Waiting (SPM conflict or bus blocking)  
- Completed  

TraceEngine은 각 DMA 명령의 start/end cycle을 기록한다.

# 12. DRAM Traffic Trace
DMAEngine은 DRAM traffic을 다음 형태로 기록한다:

```json
{
  "cycle": 12345,
  "type": "read" | "write",
  "bytes": 32,
  "dram_addr": 12000
}
```
이 정보는 다음 분석에 사용된다.

DRAM bandwidth heatmap

KV cache traffic profiling

bitwidth 변경 시 traffic 변화량 분석

transformer workload profiling

# 13. SPM Trace
SPM은 bank 충돌 정보와 access timeline을 trace로 기록한다:

```json
{
  "cycle": 12348,
  "bank": 2,
  "bytes": 32,
  "direction": "write"
}
```
이 정보는:

SPM bank conflict heatmap

SPM 용량 조정

타일링 정책 변경 효과 분석

등에 사용된다.

# 14. DMA Timing 검증 규칙
시뮬레이터는 DMA timing을 다음 규칙으로 사전 검증해야 한다.

bytes > 0

alignment 규칙 충족

SPM bank 범위 내 offset 존재

(LOAD) SPM 공간이 충분한지

(STORE) tensor shape과 offset이 유효한지

DRAM address가 0 이상인지

2D DMA에서는 shape/stride가 일관적인지

오류 발생 시 CMDQ invalid 에러 출력 후 종료.

# 15. 확장성 (Extensibility)
DMA timing 스펙은 다음을 염두에 두고 설계되었다.

multi-channel DRAM (channel interleaving)

multi-DMA-engine 지원

2D/ND DMA stride load/store

streaming DMA

sparsity-aware DMA

compress/decompress DMA

HBM 기반 구조 확장

새로운 특성을 지원할 때는
기존 공식(latency = burst + bw + contention + spm)을 변경하지 않고
새로운 penalty term 또는 scaling factor로 확장해야 한다.

# 16. 결론 (Summary)
본 문서는 DMAEngine의 timing을 결정하는 모든 요소를 정의했다.

핵심 요약:

bytes = elements * qbits / 8

alignment penalty

DRAM burst latency + bandwidth-limited latency

shared-bandwidth 기반 contention model

SPM bank conflict penalty

Prefetch semantics 지원

trace-friendly 구조 유지

DMAEngine timing 모델은
NPU Simulator의 전체 accuracy를 결정하는 핵심 요소 중 하나이며,
특히 LLM workloads에서 DRAM → KV Cache traffic이 latency의 주요 병목이므로
본 스펙은 LLM-centric NPU 시뮬레이터에서 필수적이다.
