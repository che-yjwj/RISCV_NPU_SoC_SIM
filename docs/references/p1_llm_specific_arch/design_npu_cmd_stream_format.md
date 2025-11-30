<!-- status: draft -->
# `design_npu_cmd_stream_format` 문서가 의미하는 것

이 문서는 **NPU가 실제로 실행하는 명령어(Command Stream)의 형식(spec)을 정의하는 문서**이다.

즉,

> “정적 스케줄링 결과를 어떤 명령어 형태로 NPU에게 전달할 것인가?”
> 

를 기술하는 **ISA(Instruction Set Architecture) 수준의 명령어 포맷 정의서**이다.

모바일 NPU는 **동적 스케줄링이 없고**,

**그래프 컴파일러가 만든 정적 커맨드 리스트를 그대로 실행**하기 때문에

Command Stream Format 문서는 **사실상 NPU의 실행 모델의 중심**이다.

---

# 📐 왜 중요한가?

모바일 NPU는 다음과 같은 철학을 가진다:

- NPU는 “슈퍼 단순한 실행 엔진”
- 복잡한 스케줄링은 모두 컴파일러가 한다
- 실행기는 **정해진 명령어를 순서대로 수행하는 기계**
- 명령어를 잘 정의해야 시뮬레이터가 현실성 있는 동작을 모사할 수 있음

따라서 **Command Stream Format**은 다음을 정한다:

- 어떤 명령어가 있고
- 어떤 필드를 가지며
- 각 명령어의 latency / dependency 규칙은 무엇이며
- DMA / TE / VE 같은 유닛들과 어떻게 연결되는지
- Loop, Prefill–Decode 스위칭을 어떻게 표현하는지

이 문서 없이는 **스케줄러 → 시뮬레이터 실행기로 이어지는 파이프라인**이 완성되지 않는다.

---

# 🧩 `design_npu_cmd_stream_format.md`에 포함될 핵심 섹션

아래는 실제로 문서를 구성할 때 포함되는 항목이다.

---

## 1) Command Stream 전체 개요

- NPU는 하나의 **Cmd Stream Buffer**를 읽으면서 실행
- 명령어는 고정 크기 or 가변 크기 형태
- 명령어는 TE/VE/DMA/Loop/Barrier 종류로 구성
- Prefill Cmd Stream + Decode Cmd Stream 두 개 존재 가능

---

## 2) 명령어 카테고리 (Instruction Categories)

### ✔ DMA Commands

- `DMA_LOAD`
- `DMA_STORE`
- Source/Destination address
- Byte length
- SRAM bank index
- Alignment 규칙
- Double-buffering tag

### ✔ TE Commands

- `TE_MATMUL`
- `TE_CONV` (있을 경우)
- `TE_ATTENTION_TILE`
- Tile shape (Tm, Tn, Tk)
- Weight pointer / activation pointer
- Quant scale pointer

### ✔ VE Commands

- `VE_LAYERNORM`
- `VE_RELU` / `VE_GELU`
- `VE_SOFTMAX`
- Vector length, stride

### ✔ Loop / Flow Control Commands

- `LOOP_BEGIN count=N`
- `LOOP_END`
- Prefill/Decode phase switch
- Fixed iteration only (dynamic skip 없음)

### ✔ Synchronization / Barrier Commands

- `WAIT_DMA`
- `WAIT_TE`
- `WAIT_VE`
- Stall rule 정의

---

## 3) 명령어 기본 형식 (Binary Format or Struct Format)

문서에서는 다음과 같은 형태로 정의함:

```
CMD_DMA_LOAD {
    opcode: 8-bit = DMA_LOAD
    src_addr: 32-bit
    dst_addr: 16-bit (SRAM bank + offset)
    size_bytes: 16-bit
    mem_flags: 8-bit
}

```

또는

```c
struct TE_MATMUL_CMD {
    uint8_t  opcode;
    uint8_t  tile_id;
    uint32_t A_addr;
    uint32_t B_addr;
    uint32_t C_addr;
    uint16_t Tm, Tn, Tk;
    uint8_t  precision;  // int8, fp8, bf16
};

```

이렇게 **이진 포맷(binary layout)까지 명확히 정의**하는 문서가 바로 `design_npu_cmd_stream_format`.

---

## 4) Prefill–Decode 분리 지점의 명령어

```
CMD_PHASE_SWITCH PREFILL → DECODE
CMD_KV_TRANSFER
LOOP_BEGIN(max_decode_tokens)
    CMD_DECODE_TILE_0
    CMD_DECODE_TILE_1
LOOP_END

```

이 구조는 완전히 정적이기 때문에

Command Stream에서 **Prefill Cmd와 Decode Cmd**가 명확하게 분리됨.

---

## 5) 실행 규칙 (Execution Semantics)

- DMA는 TE/VE와 병렬 가능?
- DMA는 bank conflict가 있으면 stall?
- TE/VE는 동시에 실행 가능한가?
- Loop counter는 어디에 저장되는가?
- WAIT 명령은 어느 유닛에 대한 의존성을 동기화하는가?

이 부분은 시뮬레이터에서 **파이프라인 동작**을 정확히 구현하기 위해 매우 중요함.

---

# 🧪 예: Prefill Command Stream

```
CMD_DMA_LOAD tile0_A
CMD_DMA_LOAD tile0_B
CMD_TE_MATMUL tile0
CMD_WAIT_TE
CMD_DMA_STORE tile0_out → SRAM
...
CMD_WRITE_KV layer=0 offset=0
...
CMD_PHASE_SWITCH PREFILL_END

```

---

# 🧪 예: Decode Command Stream

```
CMD_LOOP_BEGIN N
    CMD_DMA_LOAD Q_current
    CMD_DMA_LOAD K[offset]
    CMD_DMA_LOAD V[offset]
    CMD_TE_ATTENTION_TILE
    CMD_VE_SOFTMAX
    CMD_TE_MATMUL_FFN
    CMD_STORE_NEW_TOKEN
CMD_LOOP_END

```

완전히 정적.

---

# 📌 정리

### ✔ `design_npu_cmd_stream_format` 문서의 핵심은:

**“모바일 NPU가 실제로 실행하는 명령어(ISA)를 정의하는 문서”**

즉, 시뮬레이터가 실행하는 **정적 명령어 스트림의 사양서**이다.

이를 통해:

- Static Scheduling 결과물을 정확히 표현
- TE/VE/DMA의 파이프라인 모델링 가능
- Prefill/Decode 실행도 정확하게 재현
- 모바일 NPU 스타일의 낮은 전력, 높은 효율 모델링 가능