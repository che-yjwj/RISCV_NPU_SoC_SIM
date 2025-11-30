# Trace Format Specification  
**Path:** `docs/spec/trace/trace_format_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Trace / Tooling Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **NPU Simulator**가 출력하는 **Trace 파일 포맷**을 정의한다.

Trace 파일은 다음 목적을 위해 사용된다.

- **성능/병목 분석**  
  - DMA / TE / VE / Memory / KV Cache / Host 관점의 latency, utilization, bandwidth  
- **시각화 툴 입력**  
  - Gantt Chart, Bandwidth Heatmap, Utilization Graph, Layer Breakdown  
- **실험 재현 및 비교**  
  - bitwidth, 타일링, 스케줄링 변경 시 결과 비교  
- **사후 분석(Post-Mortem Analysis)**  
  - 실패/에러 케이스 디버깅, 이상 패턴 탐지  

본 스펙은 Trace 파일의 **논리 구조, JSON 스키마, 필드 의미**를 정의하며,  
Simulator와 Viewer/Profiler가 공통으로 준수해야 하는 단일 포맷이다.

---

# 2. 전체 구조 개요 (Top-Level Structure)

Trace 파일은 **JSON** 기반을 기본으로 한다.  
(추후 binary/columnar 포맷으로의 변환은 이 스펙의 파생물로 간주)

Top-level 구조:

```json
{
  "version": "1.0",
  "run_metadata": { ... },
  "config_snapshot": { ... },
  "timeline_events": [ ... ],
  "bandwidth_samples": [ ... ],
  "summary_metrics": { ... }
}
각 필드는 아래 섹션에서 상세히 정의한다.

3. version
json
Copy code
"version": "1.0"
Trace 포맷의 버전

Breaking change가 있을 경우 Major를 올려야 한다.

Viewer/Profiler는 version을 확인하여 호환성 체크를 수행해야 한다.

4. run_metadata
시뮬레이션 실행 환경/실험 조건에 대한 메타데이터.

예시:

json
Copy code
"run_metadata": {
  "run_id": "2025-11-30_ia_npu_sim_run_001",
  "timestamp": "2025-11-30T10:32:45Z",
  "model_name": "TinyLLaMA-1.1B",
  "workload_type": "LLM_PREFILL_AND_DECODE",
  "tokens": {
    "prefill_tokens": 512,
    "decode_tokens": 256
  },
  "cmdq_file": "output/cmdq/run_001_cmdq.json",
  "ir_snapshot_file": "output/ir/run_001_ir.json",
  "notes": "baseline: W4A8, KV4, 2TE+2VE"
}
필드 정의
run_id (string)

trace를 유일하게 식별하는 ID

timestamp (string, ISO 8601)

model_name (string)

workload_type (string)

예: "LLM_PREFILL", "LLM_DECODE", "VISION_CLS", "CUSTOM"

tokens (object, optional)

LLM workload일 때 prefill/decode token 수

cmdq_file (string)

이 run에서 사용한 CMDQ 파일 경로

ir_snapshot_file (string, optional)

IR snapshot 파일 경로

notes (string, optional)

5. config_snapshot
시뮬레이터 구성 상태를 snapshot으로 기록.
(TE/VE 수, DMA 채널 수, bitwidth 허용 범위 등)

예시:

json
Copy code
"config_snapshot": {
  "npu": {
    "num_te": 2,
    "num_ve": 2,
    "num_dma": 1
  },
  "timing": {
    "dma_model": "shared_bw_v1",
    "te_model": "macs_per_cycle_v1",
    "ve_model": "vector_reduce_v1"
  },
  "quantization": {
    "default_weight_qbits": 4,
    "default_activation_qbits": 8,
    "default_kv_qbits": 4
  },
  "memory": {
    "dram_peak_bw_bytes_per_cycle": 64,
    "spm_banks": 8,
    "spm_bank_size_bytes": 262144
  }
}
이 블록은 Trace만 보고도 어떤 config에서 나온 결과인지를 재현 가능하게 한다.

6. timeline_events
시뮬레이터에서 발생하는 주요 이벤트를 시간축(cycle) 기준으로 기록한 리스트.

타입은 크게 네 가지:

ENGINE_EVENT: DMA / TE / VE / HOST / 기타 엔진의 작업 단위

MEM_ACCESS_EVENT: DRAM / SPM access 단위

TOKEN_EVENT: LLM token 경계 정보

MARKER_EVENT: 사용자 정의 마커 / 구간 태그

6.1 ENGINE_EVENT
엔진(DMA/TE/VE/Host 등)의 “작업 하나”를 나타내는 레코드.

예시:

json
Copy code
{
  "type": "ENGINE_EVENT",
  "engine": "TE",
  "engine_id": 0,
  "cmdq_id": 42,
  "layer_id": "ffn_3",
  "tile_id": "ffn_3_tile_7",
  "op": "TE_GEMM_TILE",
  "start_cycle": 12000,
  "end_cycle": 12320,
  "details": {
    "m": 64,
    "n": 128,
    "k": 256,
    "qbits_weight": 4,
    "qbits_activation": 8,
    "macs": 2097152
  }
}
공통 필드
필드	타입	설명
type	string	"ENGINE_EVENT"
engine	string	"DMA", "TE", "VE", "HOST", "OTHER"
engine_id	int	해당 엔진 index (0..N-1)
cmdq_id	int	이 이벤트를 발생시킨 CMDQ entry index
layer_id	string	관련 LayerIR id (없으면 null)
tile_id	string	관련 tile id (없으면 null)
op	string	opcode 또는 논리 연산 이름
start_cycle	int	inclusive 시작 cycle
end_cycle	int	exclusive 또는 inclusive (프로젝트에서 하나로 고정)
details	object	엔진별 추가 정보

DMA 예시
json
Copy code
{
  "type": "ENGINE_EVENT",
  "engine": "DMA",
  "engine_id": 0,
  "cmdq_id": 10,
  "layer_id": "attn_5",
  "tile_id": "attn_5_k_tile_2",
  "op": "DMA_LOAD_TILE",
  "start_cycle": 8000,
  "end_cycle": 8200,
  "details": {
    "tensor_role": "kv",
    "direction": "read",
    "bytes": 2048,
    "bytes_aligned": 2048,
    "qbits": 4,
    "dram_addr": 120000,
    "spm_bank": 2,
    "spm_offset": 8192
  }
}
VE 예시
json
Copy code
{
  "type": "ENGINE_EVENT",
  "engine": "VE",
  "engine_id": 1,
  "cmdq_id": 73,
  "layer_id": "ln_3",
  "tile_id": "ln_3_tile_0",
  "op": "VE_LAYERNORM_TILE",
  "start_cycle": 15000,
  "end_cycle": 15080,
  "details": {
    "length": 4096,
    "qbits_activation": 8
  }
}
6.2 MEM_ACCESS_EVENT
보다 세밀한 DRAM/SPM access 수준의 기록이 필요할 때 사용.

예시:

json
Copy code
{
  "type": "MEM_ACCESS_EVENT",
  "mem_type": "DRAM",
  "cycle": 8010,
  "direction": "read",
  "bytes": 32,
  "addr": 120000,
  "source_engine": "DMA",
  "source_engine_id": 0,
  "cmdq_id": 10
}
필드 정의
필드	타입	설명
type	string	"MEM_ACCESS_EVENT"
mem_type	string	"DRAM", "SPM"
cycle	int	access가 일어난 cycle
direction	string	"read", "write"
bytes	int	access bytes
addr	int	DRAM/ SPN address
source_engine	string	요청을 발생시킨 엔진
source_engine_id	int	엔진 index
cmdq_id	int	연관된 CMDQ entry id

초기 버전에서는 DRAM만 기록하고,
SPM은 옵션으로 둘 수 있다.

6.3 TOKEN_EVENT (LLM 전용)
LLM 시뮬레이션에서 토큰 경계를 명확히 표현하기 위한 이벤트.

예시:

json
Copy code
{
  "type": "TOKEN_EVENT",
  "phase": "DECODE",
  "token_index": 37,
  "start_cycle": 20000,
  "end_cycle": 24000,
  "details": {
    "generated_token_id": 50256,
    "prompt_len": 512
  }
}
필드 정의
필드	타입	설명
type	string	"TOKEN_EVENT"
phase	string	"PREFILL", "DECODE"
token_index	int	decode phase에서의 token index
start_cycle	int	token 처리 시작 cycle
end_cycle	int	token 처리 완료 cycle
details	object	추가 메타데이터

Viewer는 TOKEN_EVENT를 이용해:

토큰별 latency

prefill / decode 구간 분리

KV Cache traffic per token 등 분석을 수행할 수 있다.

6.4 MARKER_EVENT
사용자 또는 시뮬레이터가 임의로 삽입하는 마커 이벤트.

예시:

json
Copy code
{
  "type": "MARKER_EVENT",
  "name": "PREFILL_DONE",
  "cycle": 18000,
  "details": {
    "note": "prefill stage finished"
  }
}
7. bandwidth_samples
주기적으로 샘플링된 DRAM bandwidth, SPM bank usage 등을 기록하는 배열.

예시:

json
Copy code
"bandwidth_samples": [
  {
    "cycle": 8000,
    "window_cycles": 64,
    "dram_read_bytes": 4096,
    "dram_write_bytes": 1024
  },
  {
    "cycle": 8064,
    "window_cycles": 64,
    "dram_read_bytes": 2048,
    "dram_write_bytes": 0
  }
]
필드 정의
필드	타입	설명
cycle	int	샘플링 윈도우 시작 cycle
window_cycles	int	샘플 길이 (cycle 수)
dram_read_bytes	int	윈도우 동안 DRAM read bytes 합
dram_write_bytes	int	DRAM write bytes 합

이 정보로부터:

per-window bandwidth (bytes/cycle → GB/s)

bandwidth heatmap

token별 bandwidth profile

등을 쉽게 계산할 수 있다.

8. summary_metrics
전체 run에 대한 집계 정보.

예시:

json
Copy code
"summary_metrics": {
  "cycles_total": 250000,
  "dram_bytes_read": 134217728,
  "dram_bytes_write": 33554432,
  "dma": {
    "utilization": 0.65,
    "max_concurrent_transfers": 2
  },
  "te": {
    "per_engine": [
      { "id": 0, "utilization": 0.72, "active_cycles": 180000 },
      { "id": 1, "utilization": 0.68, "active_cycles": 170000 }
    ]
  },
  "ve": {
    "per_engine": [
      { "id": 0, "utilization": 0.35, "active_cycles": 90000 },
      { "id": 1, "utilization": 0.38, "active_cycles": 95000 }
    ]
  },
  "kv_cache": {
    "bytes_read": 67108864,
    "bytes_written": 8388608
  },
  "tokens": {
    "prefill_latency_cycles": 120000,
    "avg_decode_latency_cycles": 500
  }
}
summary_metrics는 Trace 없이도 빠르게 비교/검색할 수 있는 정보이며,
다수의 trace를 모아 실험 결과를 정리할 때 유용하다.

9. 파일 예시 (전체 예)
간단한 예시:

json
Copy code
{
  "version": "1.0",
  "run_metadata": {
    "run_id": "run_001",
    "timestamp": "2025-11-30T10:32:45Z",
    "model_name": "TinyLLM",
    "workload_type": "LLM_DECODE",
    "tokens": { "prefill_tokens": 256, "decode_tokens": 64 },
    "cmdq_file": "cmdq/run_001_cmdq.json"
  },
  "config_snapshot": {
    "npu": { "num_te": 2, "num_ve": 2, "num_dma": 1 },
    "memory": { "dram_peak_bw_bytes_per_cycle": 64 },
    "quantization": { "default_weight_qbits": 4, "default_kv_qbits": 4 }
  },
  "timeline_events": [
    {
      "type": "ENGINE_EVENT",
      "engine": "DMA",
      "engine_id": 0,
      "cmdq_id": 0,
      "layer_id": "ffn_1",
      "tile_id": "ffn_1_tile_0",
      "op": "DMA_LOAD_TILE",
      "start_cycle": 1000,
      "end_cycle": 1100,
      "details": {
        "tensor_role": "weight",
        "direction": "read",
        "bytes": 2048,
        "bytes_aligned": 2048,
        "qbits": 4
      }
    },
    {
      "type": "ENGINE_EVENT",
      "engine": "TE",
      "engine_id": 0,
      "cmdq_id": 1,
      "layer_id": "ffn_1",
      "tile_id": "ffn_1_tile_0",
      "op": "TE_GEMM_TILE",
      "start_cycle": 1100,
      "end_cycle": 1300,
      "details": {
        "m": 64,
        "n": 128,
        "k": 256,
        "qbits_weight": 4,
        "qbits_activation": 8
      }
    },
    {
      "type": "TOKEN_EVENT",
      "phase": "DECODE",
      "token_index": 0,
      "start_cycle": 900,
      "end_cycle": 2000,
      "details": { "generated_token_id": 1234 }
    }
  ],
  "bandwidth_samples": [
    {
      "cycle": 1000,
      "window_cycles": 64,
      "dram_read_bytes": 4096,
      "dram_write_bytes": 0
    }
  ],
  "summary_metrics": {
    "cycles_total": 2000,
    "dram_bytes_read": 4096,
    "dram_bytes_write": 0
  }
}
10. 설계 철학
Trace 포맷은 다음 철학을 따른다.

Human-readable 우선 → JSON

디버깅 / 연구 단계에서 쉽게 읽고 수정 가능

나중에 binary 변환은 별도 레이어로 처리

Viewer-agnostic

특정 UI/도구에 종속되지 않는 중립 스키마

Python, JS, Rust 등 어디에서나 쉽게 파싱 가능

Spec-driven 확장

새로운 이벤트 타입 추가 시

type 필드에 새 문자열 추가

기존 필드에는 영향을 주지 않음

분리된 책임

Simulator: trace 파일 생성

Viewer/Profiler: trace 파일 소비 및 시각화/분석

포맷 스펙: 양쪽 사이의 계약(Contract)

11. Validation 규칙
Trace 파일 로더는 다음을 검증해야 한다.

version 존재 및 지원 버전인지 확인

timeline_events가 배열인지, 각 요소가 최소한 type 필드를 포함하는지

ENGINE_EVENT의 경우 start_cycle <= end_cycle

cycle 값이 음수가 아닌지

engine, mem_type, phase 등의 enum 필드가 허용 값인지

summary_metrics.cycles_total가 최소한 timeline_events의 최대 end_cycle 이상인지 (optional consistency check)

잘못된 경우:

Viewer는 warning 또는 error를 출력해야 한다.

Simulator는 가능하면 Trace에 “INVALID_TRACE” 마커를 남기고 종료하는 방식 권장.

12. 확장성 (Extensibility)
향후 다음과 같은 확장이 가능하다.

STALL_EVENT: 특정 이유(예: SPM bank conflict, DRAM queue full)로 엔진이 stall된 구간

BUS_EVENT: NoC / interconnect 레벨의 traffic

POWER_ESTIMATE: cycle window별 power/energy 추정 값

ERROR_EVENT: 시뮬레이션 중 발생한 내부 오류

새 이벤트 타입 추가 시 규칙:

type 필드를 새로운 문자열로 정의 (예: "STALL_EVENT")

추가 필드는 optional로 설계

기존 파서가 새 타입을 무시하더라도 문제 없도록 해야 함

13. 결론 (Summary)
trace_format_spec.md는 NPU Simulator의 결과를 기록하는 단일 Trace 포맷 스펙이다.

run_metadata / config_snapshot → 실험 조건 재현

timeline_events → Gantt / utilization / token-level latency 분석

bandwidth_samples → DRAM bandwidth heatmap

summary_metrics → 실험 간 빠른 비교

이 스펙을 기준으로 Simulator와 Viewer를 구현하면,
LLM/NPU 아키텍처 실험에서 정량적인 병목 분석과 시각화가 가능해진다
