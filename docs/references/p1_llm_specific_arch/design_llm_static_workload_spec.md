**모바일 NPU용 정적 LLM 워크로드 사양서 (Workload Specification Document)**

Version 1.0

---

## 1. 목적

본 문서는 정적 스케줄링 기반 모바일 NPU 시뮬레이터에서 사용할

**LLM 워크로드(Workload)를 생성하기 위한 입력 규격 및 구성 규칙**을 정의한다.

이 문서는 다음을 기반으로 한다:

- `design_llm_prefill_decode_static.md`
- `design_static_tile_scheduler.md`
- `design_static_memory_planner.md`
- `design_npu_cmd_stream_format.md`

즉, “LLM 추론 전체를 구성하는 정적 workload를 어떻게 기술하고 제공하는가”를 명확히 한다.

---

## 2. 워크로드 구조 개요

워크로드는 아래 두 개의 “정적 수행 단계(Static Phases)”로 구성된다.

1. **Prefill Phase**
2. **Decode Phase**

모바일 NPU 시뮬레이터는 이 두 phase를 *서버처럼 동적으로 스케줄*하지 않고,

컴파일러가 생성한 **정적 Command Stream**을 그대로 수행한다.

### 전체 워크로드 흐름:

```
[Workload Input JSON]
        ↓
[Graph Lowering]
        ↓
[Static Tiling]
        ↓
[Static Memory Planning]
        ↓
[Prefill Static Schedule]  →  Prefill Cmd Stream
[Decode Static Schedule]   →  Decode Cmd Stream

```

이 문서는 **맨 처음 입력(Workload Input JSON)**의 형식과 내용을 정의한다.

---

## 3. 워크로드 입력(Workload Input) 포맷 정의

워크로드 입력은 JSON 형태로 전달된다.

### 3.1 Top-Level 구조

```json
{
  "model": { ... },
  "prefill": { ... },
  "decode": { ... },
  "memory": { ... },
  "constraints": { ... }
}

```

---

## 4. Model 섹션

LLM 모델의 핵심 파라미터를 명시한다:

```json
"model": {
  "num_layers": 32,
  "hidden_dim": 4096,
  "head_dim": 128,
  "num_heads": 32,
  "ffn_dim": 11008,
  "weight_precision": "int8",
  "activation_precision": "fp16"
}

```

추가 항목:

- rotary embedding 적용 여부
- kv-cache data type
- tensor parallel 여부 (모바일 NPU에서는 대부분 없음)

---

## 5. Prefill Workload 정의

Prefill은 **정적 그래프**이므로 다음 필드를 필요로 한다.

```json
"prefill": {
  "max_seq_len": 4096,
  "input_size_bytes": 16384,
  "required_layers": "all",
  "attention": { "mode": "full" },
  "kv_cache_write": true}

```

Prefill의 목적:

- 입력 문맥 전체를 처리
- KV Cache를 레이어별로 생성
- Prefill 타일 스케줄링이 수행됨

---

## 6. Decode Workload 정의

LLM Decode는 정적 반복(Loop)이므로 다음을 명시:

```json
"decode": {
  "max_new_tokens": 128,
  "kv_read_stride_bytes": 128 * 128,
  "decode_graph": "static_token_step",
  "loop_mode": "fixed"
}

```

Decode Phase의 목적:

- Prefill에서 생성한 KV Cache를 참조
- Token-by-token pipeline
- latency critical

---

## 7. Memory 섹션

모바일 NPU 시뮬레이터가 필요한 정적 메모리 요구사항을 명시한다.

```json
"memory": {
  "sram_size_kb": 512,
  "sram_banks": 8,
  "dram_bandwidth_gbps": 34,
  "kv_cache_layout": "static",
  "weight_compression": "int4_pack"
}

```

다음 필드를 지원:

- SRAM bank conflict model
- DRAM latency model
- Weight cache level (some NPUs have L2 weight cache)

---

## 8. Constraints (정적 제약 조건)

모바일 환경에서는 다음 제약을 반드시 명시할 수 있다.

```json
"constraints": {
  "thermal_budget_mw": 4500,
  "max_power_mw": 3500,
  "latency_target_ms": 200,
  "prefill_tile_policy": "max_throughput",
  "decode_tile_policy": "min_latency"
}

```

타일 스케줄러가 사용할 정책(policy)을 고정적으로 명시한다.

---

## 9. Prefill/Decode 출력물: Static Tile DAG

### Prefill Tile DAG 예:

```json
"prefill_tile_dag": [
  { "op": "q_matmul", "tile_id": 0 },
  { "op": "k_matmul", "tile_id": 1 },
  ...
]

```

### Decode Tile DAG 예:

```json
"decode_tile_dag": [
  { "op": "q_proj", "tile_id": 100 },
  { "op": "kv_read", "tile_id": 101 },
  ...
]

```

이 DAG는 Tile Scheduler의 입력이 된다.

---

## 10. Tile Scheduler Output과 연결

워크로드 사양은 Tile Scheduler가 다음과 같은 출력을 생성하도록 유도한다:

- Prefill Static Tile Schedule
- Decode Static Tile Schedule
- Tile-level latency estimate
- SRAM allocation map
- DMA tile plan
- Command Stream Generator가 읽을 수 있는 구조

---

## 11. Command Stream Generator와 연결

워크로드에 의해 생성되는 최종 산출물:

1. `prefill_cmd_stream.bin`
2. `decode_cmd_stream.bin`
3. `static_timeline.json` (optional)
4. `memory_map.json`

모바일 NPU 시뮬레이터는 이 **정적 객체들**을 읽어 실행한다.

---

# ✔ 최종 요약

이 문서는:

> 정적 스케줄링 기반 모바일 NPU 시뮬레이터에서
LLM 실행을 위한 워크로드를 생성하기 위한
입력 규격 / 구성 규칙을 정의하는 문서이다.
> 

이 문서를 기반으로:

- Prefill/Decode 분리
- Tile Scheduler
- Memory Planner
- Command Stream Generator

가 모두 연동된다.