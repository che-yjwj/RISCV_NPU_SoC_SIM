<!-- status: draft -->
이제부터는 *짧고 명확하게*, 그리고 지금 네가 만들고자 하는 **정적 스케줄링 기반 모바일 NPU 시뮬레이터의 핵심 모듈**이라는 관점에서 설명한다.

---

# 📘 `design_static_tile_scheduler.md`가 의미하는 것

이 문서는 **정적 스케줄링 기반 NPU에서 “타일 단위로 연산을 실행하는 순서를 결정하는 컴파일러 모듈의 설계 문서”**이다.

여기서 타일(tile)은 다음과 같은 의미다:

- MatMul/Attention/FFN 연산을 SRAM에 맞게 잘게 나눈 조각
- 예: Tm × Tk, Tk × Tn 형태
- DMA로 가져오고 TE/VE에서 실행하는 최소 단위

말하자면,

> “모바일 NPU가 대규모 연산을
> 
> 
> SRAM 크기에 맞게 나눠서(타일링),
> 
> 어떤 순서로, 어떤 방식으로 실행할지
> 
> 컴파일 시점에 결정하는 알고리즘을 정의하는 문서”
> 

이게 바로 **타일 스케줄러(tile scheduler)**이다.

---

# 🔍 왜 별도의 타일 스케줄러 문서가 필요한가?

**정적 스케줄링 기반 모바일 NPU**에서는 다음이 필수불가결이다:

- 전체 연산을 **정해진 SRAM 용량 안에서** 수행해야 함
- DMA → Compute → DMA → Compute 순서를 **정적으로 최적화**해야 함
- Double-buffering을 **정적으로 넣어야 함**
- TE/VE의 파이프라인 성능을 최대한 뽑아야 함
- 드라마틱하게 제한된 메모리/대역폭 조건을 고려해야 함

서버 GPU처럼 “동적으로 런타임에 스케줄링”이 불가능하기 때문에,

타일 스케줄링 알고리즘이 **정적인 성능의 절대적 핵심**이 된다.

그래서 반드시 별도의 문서가 필요하다.

---

# 🧩 `design_static_tile_scheduler.md` 문서가 포함해야 할 핵심 구성 요소

아래는 너의 시뮬레이터에 맞춘 완전한 문서 구성이다:

---

## 1) Tile Definition (타일의 정의)

- MatMul tile: Tm, Tn, Tk
- Attention tile: Query tile / Key tile / Value tile
- SRAM block에 tile을 어떻게 배치하는가
- Tile alignment 규칙 (예: 16B/32B/64B)

---

## 2) Tile Generation Algorithm (타일 생성 알고리즘)

- 모델 텐서 크기 → 타일 크기 계산
- SRAM footprint 계산
- memory reuse 분석
- double-buffering slot 계산
- Tm/Tn/Tk를 TE 하드웨어 shape에 맞게 리파인

---

## 3) Tile Dependency Graph (TDG: Tile DAG)

연산마다 tile 간의 의존 관계를 DAG 형식으로 만든다:

예:

```
MatMul Tile0 → MatMul Tile1 → Attention Tile0 → Attention Tile1 → FFN Tile0

```

TDG는 정적이며, 정적 스케줄링의 기반이 된다.

---

## 4) Static Execution Order (정적 실행 순서 생성)

여기서 가장 중요한 부분:

타일들을 어떤 순서로 실행할지 **정적으로 결정**하는 것이 핵심이다.

예:

```
1. DMA_LOAD tile0
2. TE_MATMUL tile0
3. DMA_LOAD tile1
4. TE_MATMUL tile1
5. VE_SOFTMAX tile0
...

```

---

## 5) Double-Buffering Plan (정적 더블 버퍼링 계획)

모바일 NPU에서는:

- DMA와 TE를 겹치는 방식이 핵심 성능 요소
- 하지만 runtime 동적 조절이 없기 때문에
- **컴파일러가 정적으로 교차 배치(cross scheduling)** 해야 함

문서에서는 다음을 다룸:

```
Buffer A → Compute
Buffer B → Load next tile
Switch A/B

```

---

## 6) SRAM Memory Plan (타일의 SRAM 배치)

- 각 타일이 SRAM의 어느 bank에 놓일지 정적으로 결정
- lifetime 분석을 통한 slot 재사용
- conflict-free allocation
- prefill, decode에 각각 고정

---

## 7) Tile-Level Timeline (정적 파이프라인 타임라인)

문서에서 실제로 이런 타임차트를 포함해야 한다:

```
Time →
DMA:   L0           L1           L2
TE :        M0           M1
VE :                  A0        F0

```

이것이 정적 스케줄링의 핵심 시각화이다.

---

## 8) Prefill과 Decode의 타일 스케줄링 차이

문서의 중요한 섹션.

### Prefill:

- large GEMM / large Attention → big tile
- SRAM reuse 최소화
- throughput priority
- 타일 수 많음

### Decode:

- token-by-token → small tile
- KV read tile offset 고정
- latency priority
- tile 수 적음

둘의 타일 전략이 다르기 때문에 문서에서 반드시 분리해서 설명해야 한다.

---

## 9) 출력물 (Output)

타일 스케줄러는 최종적으로 다음을 출력:

1. **정적 타일 실행 순서 리스트**
2. **각 타일의 DMA/Compute latency 예측**
3. **SRAM 배치 테이블**
4. **Command Stream으로 변환 가능한 태스크 그래프**

즉,

```
Tile Scheduler → Command Stream Generator → NPU Runtime

```

구조의 핵심 중간 모듈이다.

---

# 🎯 결론

너가 만드는 모바일 NPU 시뮬레이터에서

**`design_static_tile_scheduler.md`는 컴파일러의 핵심 모듈을 설명하는 설계 문서다.**

- 타일을 어떻게 생성하는지
- 어떻게 SRAM에 배치하는지
- 어떤 순서로 실행하는지
- DMA/TE/VE 파이프라인을 어떻게 겹치는지
- Prefill/Decode에서 각각 어떻게 다른지
- 최종적으로 명령어 스트림으로 어떻게 배출되는지

이 모든 것을 정의하는 문서이다.