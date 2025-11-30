# Profiler & Trace Format Specification (v1)

## 1. Purpose & Scope
본 문서는 RISC-V + xNPU ISA 기반 NPU 시뮬레이터에서 사용되는 **프로파일러 및 트레이스 포맷(JSON)**을 정의한다.

목표:
- CPU/NPU/Memory/NoC 이벤트를 일관된 스키마로 기록하기 위한 JSON 기반 trace 포맷 정의
- 시간 축(timeline) 및 리소스 축(TE/VE/DMA/DRAM/SRAM)에 대한 시각화 뷰어 연동을 염두에 둔 필드 설계
- 멀티테넌시, LLM Phase, xNPU ISA 명령 단위의 분석이 가능한 level의 granularity 제공

---

## 2. Design Principles
1. **단일 Event Stream + 명확한 타입 필드**: `event_type`을 기준으로 다양한 이벤트를 하나의 log에서 처리
2. **시간 기반 분석 최우선**: `t_cycle` 또는 `t_ns` 기반 timeline 분석에 용이하도록 설계
3. **멀티 리소스 분석 지원**: CPU, TE, VE, DMA, DRAM, SRAM, NoC를 공통 필드로 표현
4. **LLM-특화 메타데이터 지원**: layer, head, phase, token index 등의 필드를 옵션으로 포함
5. **뷰어-친화적인 구조**: 프론트엔드(웹 뷰어, Jupyter, CLI)에서 쉽게 파싱/필터링 가능하도록 flat JSON 사용

---

## 3. Trace File Structure

### 3.1 파일 단위 구조
- 파일 형식: JSON Lines (한 줄당 하나의 event JSON)
- 확장자: `.jsonl` 또는 `.trace.jsonl`

예시:
```json
{"event_type": "CMD_ENQUEUE", "t_cycle": 100, ...}
{"event_type": "DMA_START",   "t_cycle": 120, ...}
{"event_type": "TE_START",    "t_cycle": 130, ...}
```

### 3.2 공통 메타 필드
모든 이벤트에 공통적으로 포함되는 필드:

```json
{
  "event_type": "TE_START",       // 이벤트 종류
  "t_cycle": 12345,                // 시뮬레이터 cycle 기준 시간
  "t_ns": 123.45,                  // 선택적, 시간 변환값(ns)
  "sim_id": "run_2025_11_25_01", // 시뮬레이션 런 ID
  "core_id": 0,                    // CPU core ID 또는 NPU core ID
  "npu_id": 0,                     // 멀티 NPU 시스템 고려
  "tenant_id": 1,                  // 멀티테넌시/프로세스/모델 ID
  "thread_id": 0                   // 향후 확장용
}
```

---

## 4. Event Types

### 4.1 명령(Command) 관련 이벤트

#### 4.1.1 CMD_ENQUEUE
- 설명: xNPU ISA 또는 MMIO를 통해 CommandQueue에 명령이 enqueue될 때 발생

```json
{
  "event_type": "CMD_ENQUEUE",
  "t_cycle": 100,
  "cmd_id": 42,
  "cmd_type": "MATMUL",               // xNPU op type
  "source": "ISA",                    // ISA or MMIO
  "token": 10,
  "desc_addr": 140737488355328,
  "layer_id": 3,
  "block_id": 3,
  "phase": "QKV_PROJ",               // LLM execution spec 기준
  "model_name": "llama2_7b"
}
```

#### 4.1.2 CMD_START / CMD_END
- 설명: command-level 실행 시작/종료 시점

```json
{
  "event_type": "CMD_START",
  "t_cycle": 150,
  "cmd_id": 42
}
{
  "event_type": "CMD_END",
  "t_cycle": 900,
  "cmd_id": 42,
  "status": "OK"                      // 또는 ERROR, TIMEOUT 등
}
```

---

### 4.2 Job-Level 이벤트 (MicroScheduler 내부)

#### 4.2.1 JOB_ISSUE
```json
{
  "event_type": "JOB_ISSUE",
  "t_cycle": 200,
  "job_id": 1001,
  "cmd_id": 42,
  "job_type": "TE_GEMM",            // TE_GEMM, VE_LN, VE_SOFTMAX, DMA_READ 등
  "tile_id": 5,                      // TE tile index
  "vec_chunk_id": null,              // VE job일 때 사용
  "phase": "QKV_PROJ"
}
```

#### 4.2.2 JOB_DONE
```json
{
  "event_type": "JOB_DONE",
  "t_cycle": 260,
  "job_id": 1001,
  "cmd_id": 42,
  "job_type": "TE_GEMM",
  "latency_cycles": 60
}
```

---

### 4.3 DMA 이벤트

#### 4.3.1 DMA_START
```json
{
  "event_type": "DMA_START",
  "t_cycle": 210,
  "tx_id": 500,
  "channel": 0,
  "direction": "DRAM_TO_SRAM",
  "src_addr": 140737488355328,
  "dst_addr": 4096,
  "size_bytes": 65536,
  "cmd_id": 42,
  "job_id": 1001,
  "phase": "QKV_PROJ"
}
```

#### 4.3.2 DMA_END
```json
{
  "event_type": "DMA_END",
  "t_cycle": 260,
  "tx_id": 500,
  "channel": 0,
  "cmd_id": 42,
  "job_id": 1001
}
```

---

### 4.4 TE/VE 이벤트

#### 4.4.1 TE_START / TE_END
```json
{
  "event_type": "TE_START",
  "t_cycle": 230,
  "job_id": 1001,
  "cmd_id": 42,
  "m": 128,
  "n": 128,
  "k": 256,
  "tile_m": 64,
  "tile_n": 64,
  "tile_k": 64,
  "phase": "QKV_PROJ"
}
{
  "event_type": "TE_END",
  "t_cycle": 280,
  "job_id": 1001,
  "cmd_id": 42,
  "mac_count": 4194304,
  "latency_cycles": 50
}
```

#### 4.4.2 VE_START / VE_END
```json
{
  "event_type": "VE_START",
  "t_cycle": 300,
  "job_id": 1100,
  "cmd_id": 43,
  "op_type": "LAYERNORM",
  "len": 4096,
  "batch": 128,
  "phase": "LN1"
}
{
  "event_type": "VE_END",
  "t_cycle": 340,
  "job_id": 1100,
  "cmd_id": 43,
  "latency_cycles": 40
}
```

---

### 4.5 Memory / SRAM / Bank Conflict 이벤트

#### 4.5.1 SRAM_ACCESS
```json
{
  "event_type": "SRAM_ACCESS",
  "t_cycle": 235,
  "addr": 8192,
  "bank_id": 1,
  "access_type": "READ",             // READ or WRITE
  "by": "TE",                         // TE, VE, DMA
  "conflict": false,
  "cmd_id": 42,
  "job_id": 1001
}
```

#### 4.5.2 SRAM_CONFLICT
```json
{
  "event_type": "SRAM_CONFLICT",
  "t_cycle": 236,
  "bank_id": 1,
  "num_requests": 3,
  "allowed": 1,
  "stalled_clients": ["VE", "DMA"],
  "cmd_id": 42
}
```

---

### 4.6 DRAM / NoC 이벤트

#### 4.6.1 DRAM_TX_START / DRAM_TX_END
```json
{
  "event_type": "DRAM_TX_START",
  "t_cycle": 220,
  "tx_id": 500,
  "channel": 1,
  "size_bytes": 65536,
  "cmd_id": 42
}
{
  "event_type": "DRAM_TX_END",
  "t_cycle": 260,
  "tx_id": 500,
  "channel": 1
}
```

#### 4.6.2 NOC_TX_START / NOC_TX_END
```json
{
  "event_type": "NOC_TX_START",
  "t_cycle": 218,
  "tx_id": 500,
  "link_id": 0,
  "size_bytes": 65536,
  "cmd_id": 42
}
{
  "event_type": "NOC_TX_END",
  "t_cycle": 258,
  "tx_id": 500,
  "link_id": 0
}
```

---

### 4.7 Interrupt / Token 이벤트

#### 4.7.1 IRQ_EMIT
```json
{
  "event_type": "IRQ_EMIT",
  "t_cycle": 900,
  "cmd_id": 42,
  "token": 10,
  "irq_line": 3
}
```

#### 4.7.2 TOKEN_COMPLETE
```json
{
  "event_type": "TOKEN_COMPLETE",
  "t_cycle": 900,
  "token": 10,
  "cmd_id": 42,
  "status": "OK"
}
```

---

### 4.8 오류/경고 이벤트

#### 4.8.1 ERROR
```json
{
  "event_type": "ERROR",
  "t_cycle": 905,
  "component": "DMA",
  "code": "ADDR_ALIGN",
  "msg": "unaligned DMA source address",
  "cmd_id": 42,
  "job_id": 1001
}
```

#### 4.8.2 WARN
```json
{
  "event_type": "WARN",
  "t_cycle": 700,
  "component": "TE",
  "code": "LOW_UTIL",
  "msg": "TE utilization below 50% in last 1000 cycles",
  "layer_id": 3
}
```

---

## 5. LLM-Specific Metadata
LLM/Transformer 분석을 위해 다음 필드를 선택적으로 포함할 수 있다.

- `layer_id`: Transformer layer index
- `block_id`: 동일 의미, 구현체에 따라 사용
- `phase`: QKV_PROJ, ATTENTION_SCORE, ATTENTION_APPLY, MLP 등
- `head_id`: multi-head attention head index
- `token_idx`: 현재 토큰 인덱스
- `seq_len`: 현재 시점의 sequence 길이
- `model_name`: LLM 모델 명칭
- `precision`: FP16/BF16/INT8 등

이 필드는 event 타입에 따라 일부 또는 전부가 포함될 수 있다.

---

## 6. Viewer Integration Assumptions

### 6.1 기본 필터링 축
Trace 뷰어는 다음 축을 기준으로 필터링/색칠을 지원한다고 가정한다.
- time: `t_cycle`/`t_ns`
- component: CPU, TE, VE, DMA, DRAM, SRAM, NOC
- cmd_id / job_id / tx_id
- layer_id / phase / head_id / token_idx
- tenant_id / model_name

### 6.2 시각화 유형
1. **Gantt Chart**
   - x축: 시간, y축: 리소스(TE/VE/DMA/DRAM) 또는 command/job
   - TE_START/END, VE_START/END, DMA_START/END, CMD_START/END 사용

2. **Timeline View**
   - 이벤트 점(event markers)을 시간순으로 나열

3. **Heatmap / Histogram**
   - DRAM BW, NoC BW, TE/VE utilization vs time

4. **Phase-level Summary**
   - LLM Phase 별 latency/ BW/ stall 분석

---

## 7. Performance Metrics Derivation

Trace로부터 다음과 같은 지표를 계산할 수 있다.

- TE utilization: TE가 busy인 cycle 비율
- VE utilization: VE busy cycle 비율
- DMA BW: `sum(size_bytes) / total_time`
- DRAM channel utilization: 채널별 busy time 비율
- SRAM bank conflict rate: `SRAM_CONFLICT` 이벤트 수 / `SRAM_ACCESS` 이벤트 수
- Phase별 latency: 각 phase의 CMD_START~CMD_END 시간
- Per-layer latency & breakdown: TE vs VE vs DMA 비중

이 지표들은 offline 분석기 또는 뷰어에서 계산한다.

---

## 8. Configuration & Versioning

### 8.1 Trace Header (Optional)
파일 맨 앞에 meta line을 둘 수 있다.
```json
{"event_type": "TRACE_META", "version": "1.0", "sim_config": {"te_tflops": 64, "sram_size": 8388608}}
```

### 8.2 Versioning
- `version`: trace 스키마 버전
- `sim_version`: 시뮬레이터 버전

버전이 변경될 때는 필드 추가/삭제를 명시해야 한다.

---

## 9. Implementation Notes

- Python에서는 `dataclasses` 또는 간단한 dict 기반으로 이벤트를 생성한 뒤 JSON lines로 flush
- 대형 trace의 경우 압축(gzip) 저장 권장
- offline 분석 시 pandas, polars 등을 활용

---

## 10. 향후 확장

1. Hierarchical trace (thread 단위/SM 단위 등 계층적 구조) 지원
2. OpenTelemetry, Chrome Trace Format 등의 외부 표준 포맷으로 내보내기(export)
3. 실측 HW 카운터와의 매핑 정의 (HW ↔ 시뮬레이터 trace alignment)
4. Energy/Power 이벤트 타입 추가 (access당 energy, power state 전환 등)

---
