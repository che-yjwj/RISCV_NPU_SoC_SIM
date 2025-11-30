# ✅ 0. 모바일 NPU는 “정적 스케줄링”이 핵심이다

서버형(NVIDIA/H100, TPU, CPX) → 동적 스케줄링, QoS, multi-session, prefill/decode 분리

모바일형(Samsung NPU, Qualcomm Hexagon, Apple ANE) → 정적 스케줄링 기반 오프로딩

모바일 NPU는 다음 특성을 갖습니다:

- **한 번 딱 정해진 모델을 매우 효율적으로 실행**
- **동적보다는 정적 실행 계획을 미리 생성**
- CPU/OS 레벨에서 multi-session scheduling을 하지 않음
- 실시간성(카메라/ISP/온디바이스 AI)에 최적화
- 대부분 **Graph Compiler → Static Scheduling → NPU Command Stream** 구조

따라서:

### ✔ 당신 시뮬레이터는

- **정적 스케줄링 기반, 타일링도 정적으로 고정**,
- Prefill/Decode 같은 “동적 phase 전환”도 **모바일에서는 필요 없음**,
- KV Cache도 디코딩용으로만 단순 성장시키는 구조도 **정적 계획 안에 포함**.

---

# 🎯 1. 정적 스케줄링 기반 LLM 추론 구조 정의

LLM이라도 모바일에서는 다음처럼 “정적 플로우”로 바라봅니다:

### **Phase 1: Prefill (1회 실행, 길이가 크지만 딱 한번)**

- 입력 길이가 정해져 있다면(예: 앱에서 max 4096 tokens로 제한)
- Prefill 전체 그래프는 **정적 스케줄링**으로 컴파일 가능
- KV Cache write 위치도 정적으로 계산 가능 (layer, head, offset)

### **Phase 2: Decode (반복 실행, 정해진 반복 구조)**

- 토큰 1개 생성 → 정적 Graph
- N번 반복 → 루프 형태 (unrolled or loop-instruction)
- KV 읽기 위치는 index 기반으로 정적으로 계산 가능
- 메모리 layout도 고정

즉:

> LLM 추론도 모바일에서는 Prefill Graph + Decode Graph의 단순 반복으로
> 
> 
> 완전히 정적 스케줄링이 가능하다.
> 

이는 실제 Apple/Qualcomm도 같은 방식으로 모델을 실행함.

---

# 🎯 2. 모바일 NPU용 정적 스케줄링 핵심 철학

### **Mobile NPU Scheduler의 5가지 진실**

1. **모든 연산의 타일링은 컴파일 시 사전 결정 (Static Tile Scheduler)**
2. **운영 중에 동적 스케줄링 없음 (No runtime dispatch ordering)**
3. **모든 DMA, SRAM 배치도 Static**
4. **모든 TE/VE 처리 순서도 Static**
5. **KV Cache Layout도 Static** (입력 길이가 bound되어 있다면)

# 🧩 3. 모바일 NPU용 정적 스케줄링 설계 문서 (핵심)

아래 문서는 **당신의 시뮬레이터에 바로 들어갈 최종 구조**로 작성했습니다.

---

# design_static_scheduler_mobile_npu.md

**모바일 NPU용 정적 스케줄링 LLM 워크로드 모델**

---

## 1. 목표

삼성/퀄컴/애플 등 **모바일 SoC NPU의 특성에 맞춘 정적 스케줄링 기반 LLM 추론 시뮬레이터**를 설계한다.

특징:

- Runtime Scheduling 없음
- Graph Compile 단계에서 전체 스케줄이 결정
- Prefill/Decode는 “두 개의 정적 서브그래프”로 취급
- 모든 타일링/메모리 배치/엔진 할당을 컴파일 시점에 결정
- NPU는 커맨드 스트림만 순차 실행 (simple command executor)

---

## 2. 전체 구조

```
PyTorch/ONNX → Graph Lowering → Static Tiling → Static Scheduling → NPU Cmd Stream → Execution

```

중심이 되는 것은:

### ✔ **Static Tiling & Scheduling Pass**

여기서 다음 정보를 모두 미리 계산:

- 모든 MatMul/Attention의 타일 크기
- 각 tile의 DMA 패턴
- layer 별 KV offset
- Prefill output → Decode input 연결
- 반복 Decode Step의 Loop Command 생성
- SRAM block 배치 (Static Memory Planner)
- TE/VE 실행 순서 (Static Engine Allocation)

---

## 3. Prefill / Decode의 정적 모델링

### 3.1 Prefill = 길이 L_prefill을 가진 **정적 Graph**

```
PREFILL_GRAPH:
    Layer 0:
        MatMul Q/K/V
        Attention
        FFN
    Layer 1:
        ...
    Layer N-1:
        KV write (fixed offset)

```

- 모든 중간 activation 크기, 오프셋, DMA offset이 **정적으로 계산 가능**
- Prefill 실행 순서 또한 graph topology로 고정

### 3.2 Decode = Token 1개 생성 그래프 (정적 Graph)

```
DECODE_STEP_GRAPH:
    Layer 0:
        Q 생성
        K/V read at offset = (prefill_len + t) * head_dim
        Attention single-step
        FFN
    Layer 1:
        ...

```

### 3.3 Decode 반복 구조

토큰 `t=0..T-1`을 생성하기 위해:

- `DECODE_STEP_GRAPH`를 NPU instruction의 “loop mode” 또는 unrolled 형태로 넣는다.

---

## 4. 정적 KV Cache Layout

KV Cache는 다음처럼 정적으로 레이어별 메모리 영역에 배치:

```
Layer0_K: base + 0
Layer0_V: base + K0_size
Layer1_K: base + L0_size
Layer1_V: ...
...

```

Decode에서는 offset 계산도 정적:

```
decode_offset = (prefill_len + t) * head_dim

```

DMA 명령:

```
DMA_READ K[layer][decode_offset]
DMA_READ V[layer][decode_offset]

```

이 모든 주소 및 바이트 크기는 **컴파일 시점에 완전히 결정**됨.

---

## 5. 정적 스케줄링 알고리즘

### 5.1 Inputs

- Graph (Prefill, Decode Step)
- NPU spec (SRAM, TE/VE count, DMA BW, alignment rule)
- Input shape bounds (max prefill length, max decode length)

### 5.2 Steps

### Step 1 — Layer Fusion / Lowering

- MatMul → TileMatMul
- MHA → (QKV Projection → AttentionTile → Output Projection)
- FFN → (MatMul1 → Activation → MatMul2)

### Step 2 — Tile Generator

각 operator마다:

- (M, N, K) tile
- SRAM tile 배치
- DMA tile 패턴 생성
- double-buffering 계획

### Step 3 — Static Memory Planner

- KV Cache 주소 결정
- 각 Tile activation을 어떤 SRAM block에 둘지 고정
- lifetime 분석으로 SRAM 재사용 (static reuse graph)

### Step 4 — Static Engine Allocation

각 tile을:

- TE or VE 중 어디서 처리할지 미리 고정
- 예:
    - large GEMM → TE
    - softmax/LN/activation → VE

### Step 5 — Global Execution Order 생성

다음 순서로 완전히 고정된 instruction list 생성:

```
(Prefill Phase)
  tile0_layer0
  tile1_layer0
  ...
  tileX_layerN
  KV Write
(Decode Loop)
  LOOP T times:
    tile0_decode_layer0
    tile1_decode_layer0
    ...
    KV Append
END LOOP

```

### Step 6 — NPU Command Stream 생성

최종적으로 아래와 같은 형태:

```
CMD_DMA_LOAD A_tile0
CMD_TE_MATMUL tile0
CMD_DMA_LOAD B_tile0
CMD_TE_MATMUL tile1
CMD_VE_SOFTMAX
CMD_DMA_WRITE KV_tile
...
CMD_LOOP_START T
   CMD_DECODE_TILE0
   CMD_DECODE_TILE1
   ...
CMD_LOOP_END

```

모든 명령은 **정적인 시점에서 완전 고정**.

---

## 6. 시뮬레이터 실행 모델

정적 스케줄링 기반 시뮬레이터는 복잡한 스케줄러가 필요 없음.

### **Runtime에는 단 하나의 루프:**

```
for cmd in command_stream:
    execute(cmd)
    update_time(cmd.latency)

```

리소스 contention은 다음 방식으로 모델링:

- TE 실행 중이면 VE는 실행 불가 (또는 병렬 허용)
- DMA 채널이 점유 중이면 다음 DMA는 stall
- SRAM bank conflict 규칙

그러나 **명령 순서는 변하지 않음.**

---

# 🔥 핵심 요약

### ✔ 당신의 모바일 NPU 시뮬레이터는:

- **정적 스케줄링 100%**
- Prefill Graph → 정적 타일 스케줄
- Decode Step Graph → 정적 타일 스케줄
- Token 반복 → static loop
- KV offset도 정적
- DMA도 정적
- TE/VE mapping도 정적

즉, “Rubin CPX처럼 동적 워크로드 분리”는 필요 없습니다.

### ✔ 모바일용이라면:

- 동적 QoS 없음
- 동적 priority 없음
- multi-session 없음
- dynamic late-binding 없음
- 모든 것이 graph compile 시점에서 확정됨
- “서버향 AI scheduling”과 완전히 철학이 다름