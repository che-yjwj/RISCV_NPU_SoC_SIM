<!-- status: draft -->
앞에서 설계했던 구조 중 **LLM 프리필·디코딩을 “정적 스케줄링 기반으로 분리하는 방식”**만을 따로 묶어 정리하는 **전용 설계 문서**야.

즉, 이것은 전체 모바일 NPU 아키텍처 문서 중에서도:

> “LLM 추론을 Prefill / Decode 두 단계로 나누고,
> 
> 
> 모바일 NPU에서는 이 두 단계를 **정적 스케줄링(static scheduling)**으로 어떻게 컴파일하고 실행하는가?”
> 

를 전문적으로 다루는 **중심 기술 문서**가 된다.

아래에 그 의미와 구성 요소, 왜 필요한지를 명확하게 정리해 줄게.

---

# 📘 `design_llm_prefill_decode_static.md`란 무엇인가?

### ❗ 정리하면 이 문서는:

> LLM의 Prefill Graph와 Decode Graph를 정적으로 컴파일하여
모바일 NPU에서 실행 가능한 정적 명령어 스트림으로 만드는 설계를 정의하는 문서
> 

즉, LLM을 위한 "정적 그래프 분해 + 정적 타일링 + 정적 명령화" 문서다.

### 서버형 NPU와 달리:

- dynamic phase switch 없음
- dynamic scheduler 없음
- runtime priority 없음
- KV cache eviction/dynamic growth 없음

모든 것이 **컴파일러가 사전에 결정하는 정적 계획**이라는 모바일형 철학을 반영한다.

---

# 📌 왜 별도 문서가 필요한가?

LLM은 일반 CNN/ViT 등과는 다르게:

- **Prefill**은 거대한 Seq-Len(L) 전체를 한 번에 통과시키는 그래프
- **Decode**는 fixed graph를 token마다 반복하는 구조
- 둘의 연산 패턴과 메모리 패턴이 완전히 다르기 때문에

모바일 NPU용 정적 컴파일러에서는 반드시 **두 그래프를 별도로 다뤄야** 한다.

그래야:

- Prefill 타일링은 big-batch / big-gemm에 최적화
- Decode 타일링은 small gemm + KV read에 최적화
- 서로 다른 메모리 레이아웃
- 서로 다른 command stream
- 서로 다른 SRAM reuse 전략
- 서로 다른 pipeline 계획

등을 정적으로 생성할 수 있다.

---

# 🧩 문서가 포함해야 하는 주요 항목

아래는 `design_llm_prefill_decode_static.md`가 완전한 문서로 포함해야 할 내용이다.

---

## 1) Prefill / Decode 분리 개념

- Prefill: 긴 입력을 처리하는 L×N 크기의 거대 그래프
- Decode: 단일 token 처리 그래프
- 모바일 NPU에서는 두 그래프가 **완전히 분리된 두 개의 정적 pipeline**

---

## 2) Static Prefill Graph

- 전체 레이어 순서 고정
- 타일링(Tm, Tn, Tk) 고정
- 레이어별 KV write offset 미리 계산
- Prefill 전체를 실행하는 스케줄은 **단 하나의 정적 명령 리스트**

예시:

```
PREFILL_CMD_STREAM:
  LOAD tile0
  MATMUL tile0
  LOAD tile1
  MATMUL tile1
  ...
  WRITE_KV layer0
  ...

```

---

## 3) Static Decode Step Graph

- token 1개 생성하는 graph
- KV read offset = (prefill_len + t) * head_dim (정적 수식)
- Static tile pipeline
- Loop 명령으로 T번 반복

예시:

```
DECODE_CMD_STREAM:
  LOOP_BEGIN max_new_tokens
     LOAD Q_tile
     LOAD K_tile(offset)
     LOAD V_tile(offset)
     ATTENTION_TILE
     FFN
     WRITE_TOKEN
  LOOP_END

```

---

## 4) Prefill → Decode 상태 전환의 정적 모델링

모바일 NPU에서는:

- Dynamic switch 없음
- Prefill Cmd Stream 끝 → Decode Cmd Stream 시작
- KV Cache는 정적 메모리 배치

즉:

```
[Prefill Stream] + [Decode Loop Stream] = 전체 LLM 실행

```

---

## 5) KV Cache Layout 정적 계산

문서에서 포함해야 할 핵심:

- Layer별 KV base address
- per-layer stride
- maximum prefill length bound
- decode offset 계산식
- SRAM ↔ DRAM DMA tile 패턴까지 정적화

예:

```
KV[layer].K @ DRAM_base + layer_offset
decode_K_addr = KV[layer].K + (prefill_len + t) * head_dim

```

---

## 6) Prefill/Decode 스케줄링의 정적성 (Static Scheduling Rules)

- Prefill: big GEMM oriented tile pipeline
- Decode: small GEMM token-by-token tile pipeline
- 각 tile마다
    - DMA → compute → DMA → compute 순서 완전 고정
- 각 phase의 engine 사용률, SRAM 배치, double-buffering이 사전에 모두 결정됨

---

## 7) 출력물(Output): 두 개의 정적 Command Streams

최종 산출물:

1. `prefill_cmd.bin`
2. `decode_cmd.bin`

모바일 NPU runtime은 단순히:

```
load(prefill_cmd)
execute()
load(decode_cmd)
execute_loop()

```

이것이 전체 LLM inference flow가 된다.

---

# 🛠 이 문서를 시뮬레이터에 적용하면 생기는 효과

- Prefill/Decode 공통 pipeline이 명확히 분리됨
- 메모리 사용량과 latency가 정확히 예측 가능
- Decode per-token latency가 정적 → 모바일 환경에 적합
- 서버형 AI 스케줄링 복잡도 제거
- NPU ISA 설계가 더 투명해짐
- 타일링/메모리 플래너/스케줄러가 각각 독립 모듈로 구조화됨

즉, 당신이 만들려는 모바일 NPU 시뮬레이터에서

**LLM 워크로드의 핵심 설계 문서**가 된다.