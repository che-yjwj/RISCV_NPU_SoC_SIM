# KV Cache Quantization Specification  
**Path:** `docs/spec/quantization/kv_cache_quantization_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Quantization Architect / LLM Memory Architect  
**Last Updated:** YYYY-MM-DD  

---

# 1. 목적 (Purpose)

이 문서는 **LLM용 KV Cache(K, V 메모리)** 에 대한  
**Mixed-Precision Quantization 정책 및 IR·TileGraph·CMDQ·Simulator 전 단계에서의 처리 규칙**을 정의한다.

KV Cache는 LLM 추론에서:

- 메모리 대부분을 차지하고  
- DRAM bandwidth의 핵심 병목이며  
- token 증가에 따라 선형적으로 증가하는 구조

이므로, 정확한 **bitwidth 설정(qbits_kv)** 및 **memory mapping**은  
NPU 시뮬레이터의 정확도와 LLM 성능 분석에서 필수적이다.

본 문서는 다음을 정의한다:

1. KV Cache bitwidth(qbits_kv) 정책  
2. K/V 텐서의 IR 구조  
3. KV Cache update (append) 시의 DMA/Tile 모델  
4. DRAM latency / bandwidth 영향  
5. bitwidth 변화에 따른 capacity / traffic 변화  
6. CMDQ와 Simulator에서 KV Cache가 “어떻게 표현되고 실행되는지”  

---

# 2. KV Cache의 논리 구조 개요 (LLM Context)

LLM에서 KV Cache는 아래 구조를 가진다:

K_cache: [B, H, T, D]
V_cache: [B, H, T, D]

yaml
Copy code

- B: batch  
- H: head  
- T: accumulated time-step (grows per token)  
- D: head_dim  

도출된 K_new, V_new는  
`T += 1` 형태로 cache의 마지막에 append 된다.

NPU 시뮬레이터에서 KV Cache의 정확한 bitwidth와 memory map은  
KV update traffic → DRAM bandwidth → latency의 상관관계를 분석하는 데 핵심이다.

---

# 3. KV Cache Quantization Design Goals

KV Cache 양자화는 다음 목표를 따른다.

### ✔ 3.1 Accuracy 유지  
- K/V는 attention score 계산에 직접 사용 → 지나친 quantization은 성능 저하  
- 일반적으로 4bit 또는 8bit 적용 가능  
- TileGraph 및 TE/VE timing에서 해당 값을 그대로 활용

### ✔ 3.2 DRAM 용량 절약  
KV Cache는 DRAM 상주  
→ token 수(T)가 길어질수록 memory pressure 증가  
→ qbits_kv를 줄이면 capacity 문제 해결 가능

### ✔ 3.3 DRAM traffic 절감  
- DMA LOAD TILE (attention read)  
- DMA STORE TILE (append)

KV bitwidth를 줄이면 traffic 감소 → latency 절감

### ✔ 3.4 LLM-friendly tile 구조와 결합  
- head parallelism  
- per-head KV tile  
- per-token append tile  

---

# 4. IR 레벨에서의 정의 (TensorIR / LayerIR 확장)

KV Cache quantization은 IR에서 다음 방식으로 표현된다.

---

## 4.1 TensorIR 확장

KV Cache 텐서는 다음과 같이 정의된다  
(예: `docs/spec/ir/tensor_metadata_spec.md` 기반):

```json
{
  "id": "kv_cache_layer3_head0",
  "role": "kv",
  "shape": [B, H, T, D],
  "dtype": "int4",
  "qbits": 4,
  "layout": "[B, H, T, D]",
  "storage_class": "DRAM"
}
중요한 부분:

role = "kv"

qbits = qbits_kv (4 or 8 등)

storage_class = "DRAM" (항상 DRAM 상주)

is_kv_head_split = true 가능

4.2 LayerIR: KV Update
KV Cache append는 LayerIR에서 다음과 같이 표현한다:

json
Copy code
{
  "id": "kv_update_layer3",
  "op_type": "KV_UPDATE",
  "inputs": ["k_new", "v_new", "kv_cache"],
  "outputs": ["kv_cache_out"],
  "qbits_kv": 4
}
k_new, v_new: 새로운 token의 single-step K/V

kv_cache: 기존 cache

kv_cache_out: append 결과

이 정보는 TileGraph → CMDQ로 전달된다.

5. Quantization 정책 (QConfig)
KV Cache는 다음과 같은 bitwidth 정책을 지원한다:

5.1 Global Default qbits_kv
yaml
Copy code
qbits_kv_default: 4
5.2 Per-layer override
KV Cache는 레이어별·헤드별로 bitwidth를 다르게 설정할 수 있다.

예:

yaml
Copy code
override:
  layer_3:
    kv: 4
  layer_4:
    kv: 8
5.3 Per-head override (선택)
예:

yaml
Copy code
layer_3:
  head_0: { kv: 4 }
  head_1: { kv: 4 }
  head_2: { kv: 8 }
6. TileGraph 단계에서의 KV Tile 구조
TileGraph는 KV Cache를 다음 두 개의 tile stream으로 처리한다.

Attention Read Tiles

TE tile: Q × K^T

DMA LOAD_TILE (K_tile)

DMA LOAD_TILE (V_tile) (attention 이후)

KV Update Tiles (append)

DMA LOAD old KV cache? → 필요 없음 (append이므로)

DMA STORE_TILE for K_new

DMA STORE_TILE for V_new

각 tile은 다음 필드를 갖는다:

json
Copy code
{
  "tile_type": "kv_read" | "kv_write",
  "qbits_kv": 4,
  "tile_elements": D (or T×D for read)
}
TileGraph는 KV Cache tile의 SPM mapping에는 최소한의 공간만 사용한다.
KV Cache는 대부분 DRAM에서 바로 읽고 쓰는 구조.

7. CMDQ로의 매핑
KV Cache의 DMA instructions는
CMDQ에서 명령으로 나타난다:

7.1 Attention Read (K/V load)
json
Copy code
{
  "opcode": "DMA_LOAD_TILE",
  "tensor_role": "kv",
  "qbits": 4,
  "dram_addr": 120000,
  "num_elements": 4096,
  "spm_bank": 2,
  "spm_offset": 8000
}
→ attention head마다 이 load가 발생
→ qbits=4 적용됨

7.2 KV Update (append)
json
Copy code
{
  "opcode": "DMA_STORE_TILE",
  "tensor_role": "kv",
  "qbits": 4,
  "dram_addr": 131072,
  "num_elements": 64,
  "spm_bank": 1,
  "spm_offset": 4000
}
KV update tile은 single token per head 구조

num_elements = head_dim(D)

Simulator는 qbits=4 기반 bytes 계산을 수행한다.

8. DRAM Memory Layout (Critical)
DRAM 내 KV Cache layout은 다음과 같은 형태를 가정한다.

css
Copy code
K_cache[layer_id][head][timestep][:]  
V_cache[layer_id][head][timestep][:]
즉:

scss
Copy code
[B=1][H][T][D]   (batch=1 가정)
각 timestep append는 다음 DRAM 주소로 매핑된다:

mathematica
Copy code
addr = base_addr
     + (head_index * T_max * D * qbits/8)
     + (timestep * D * qbits/8)
KV Cache의 DRAM footprint는:

ini
Copy code
bytes_total_K = H × T × D × qbits_kv/8
bytes_total_V = H × T × D × qbits_kv/8
critical insight
→ qbits_kv가 8→4로 변하면, 동일 T에서 DRAM footprint가 절반이 된다.
→ DMA load/store bytes도 절반이 된다.
→ KV Cache bitwidth가 LLM latency의 최고 영향 요인.

9. DMA Timing과 KV Cache의 결합
dma_timing_spec.md 규칙에 따라:

ini
Copy code
bytes_total = ceil( num_elements × qbits_kv / 8 )
bytes_aligned = alignment(bytes_total)
KV Cache read/write는 대부분 다음 3 패턴을 가진다:

9.1 Attention Read (heavy)
많은 tile LOAD

전체 attention head를 DRAM에서 읽어야 함

qbits=4 → qbits=8 대비 latency 절반

9.2 KV Update (light)
head_dim(D)의 크기만큼 append

traffic 작음

alignment penalty가 더 크게 보일 수 있음

9.3 Chunked Attention (optional)
T가 너무 크면 K/V를 chunk 단위로 나누어 tile load

qbits_kv 설정이 chunk traffic 계산에 직접 영향

10. Simulation 측면: KV Cache Timing 모델
Simulator에서는 KV Cache 연산이 다음 흐름으로 모델링된다:

java
Copy code
KV_READ_TILE
  ↓
DMA load latency (based on qbits_kv)
  ↓
TE tile (Q·K^T, softmax, V weighted)
  ↓
KV_WRITE_TILE
  ↓
DMA store latency (based on qbits_kv)
Latency의 대부분을 차지하는 것은 DMA load이며, 이는 qbits_kv에 직접 비례한다.

11. KV Cache에 대한 Visualization 용 메트릭
트레이스 엔진에서는 KV 관련 metric을 기록한다:

11.1 Per-token KV Traffic
arduino
Copy code
{
  "token": t,
  "bytes_k" : ...,
  "bytes_v" : ...
}
11.2 Layer별 KV Cache Memory Usage
arduino
Copy code
{
  "layer": l,
  "kv_bytes_total": ...
}
11.3 Bitwidth 변화에 따른 Latency Comparison
qbits_kv 변경 시:

DMA load cycles

total latency

DRAM bandwidth usage

의 변화를 그래프로 출력할 수 있다.

12. End-to-end Example
설정
Layers = 32

Heads per layer = 32

D = 128

T = 1024

qbits_kv = 4

DRAM footprint for K or V
python
Copy code
bytes = H × T × D × qbits_kv/8
       = 32 × 1024 × 128 × 4/8
       = 2,097,152 bytes (2MB)
즉:

qbits_kv = 8 → 4MB

qbits_kv = 4 → 2MB

qbits_kv = 2 → 1MB (확장 가능)

→ KV Cache bitwidth 조절이 DRAM memory scaling에 직접적으로 영향.

13. Validation 규칙
IR/Compiler/Simulator는 아래 규칙을 검증해야 한다.

KV 텐서는 반드시 role="kv" 여야 함

qbits_kv는 {2, 4, 8} 등 지원 목록 내에 있어야 함

KV Cache 텐서는 storage_class="DRAM"

K/V update는 shape [B, H, T, D] 구조와 일치해야 함

DRAM address 계산이 kv layout 규칙을 벗어나지 않아야 함

DMA LOAD_TILE / STORE_TILE의 num_elements는 D 또는 T×D 와 일치해야 함

오류 시 CMDQ invalid로 실패 처리.

14. 확장성 (Extensibility)
향후 다음 확장 가능:

KV Cache compression (RLE, delta coding)

dynamic bitwidth (qbits_kv를 timestep 기반으로 달리 적용)

shrink-window attention (sliding window 시 KV Cache drop)

head grouping 기반 KV layout

fp8 KV Cache

이러한 확장은 기존 qbits_kv → bytes → DMA latency 체인을 유지한 상태에서
추가 term 또는 별도 정책으로 확장해야 한다.

15. 결론 (Summary)
kv_cache_quantization_spec.md는
LLM 중심 시뮬레이터에서 가장 중요한 “KV Cache bitwidth → memory → latency”
관계를 정식 정의한 문서이다.

핵심 요약:

KV Cache는 항상 DRAM 상주, memory pressure의 핵심

qbits_kv는 Layer/Timestep/Head 단위로 독립적으로 설정 가능

qbits_kv 변경은

DRAM footprint

DMA traffic

attention latency
에 직접적으로 영향을 준다

TileGraph → CMDQ → DMA → Simulator로
모든 단계에 bitwidth가 일관되게 반영

NPU Simulator에서 LLM 성능 분석 시
KV Cache bitwidth는 가장 중요한 tuning 파라미터

본 스펙은 LLM-friendly Mixed Precision NPU 설계의
필수 기반 문서로 유지/확장되어야 한다.