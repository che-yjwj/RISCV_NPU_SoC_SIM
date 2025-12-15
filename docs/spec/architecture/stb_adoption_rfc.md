# RFC: STB(Shared Tile Buffer) 의미론 및 채택 범위

**Status:** Proposed  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-14

## 1. 배경

현재 메인 문서 트리(`docs/spec/*`, `docs/overview/*`)는 SPM(Scratchpad Memory) 기반의
타일 실행/정적 스케줄링/CMDQ 실행 모델을 전제로 한다.

과거 통합 전 문서 트랙에서 TE→VE 경계에
**STB(Shared Tile Buffer)** 라는 “디스크립터 스트림 경계(ready/valid)” 개념을 명시했다.

메인 스펙 관점에서 다음을 결정해야 한다.

- STB를 “필수 아키텍처 구성요소”로 올릴지
- 아니면 “옵션(설계 선택)”으로 둘지

## 2. 문제 정의

TE/VE가 협업하는 파이프라인에서 필요한 것은 크게 두 가지다.

1) **payload 타일 데이터의 저장/공유 지점** (SPM)  
2) **생산자→소비자 handoff를 표현하는 제어/의존성 경계** (descriptor/event boundary)

STB는 (2)를 하드웨어적으로 구현하는 한 방식이다.

## 3. 옵션

### Option A — STB를 “필수 아키텍처(물리 블록)”로 채택

- TE/VE 사이에 STB FIFO(ready/valid)를 반드시 존재시킨다.
- 장점: 의미가 명확하고, 엔진 간 back-pressure 모델이 단순하다.
- 단점: 메인 스펙의 CMDQ/ControlFSM 모델과 중복되는 제어 구조가 될 수 있다.

### Option B — STB를 “필수 의미론(semantic construct), 구현은 선택”으로 채택

- 메인 스펙에 다음을 **불변 의미론**으로 채택한다.
  - TE→VE(또는 엔진 간)에는 “타일 디스크립터 handoff 경계”가 존재한다.
  - payload는 SPM에만 존재하며, handoff는 디스크립터/이벤트로 표현된다.
- 구현은 아래 중 하나를 선택할 수 있다.
  - (B1) 하드웨어 STB(ready/valid FIFO)
  - (B2) CMDQ + 엔진 큐 + deps_before/tag-wait로 동일 의미를 구현(논리적 STB)
- 장점: 핵심 의미론을 메인에 고정하면서도 구현 다양성을 유지한다.
- 단점: 문서에서 “물리 STB vs 논리 STB” 구분을 명확히 해야 한다.

### Option C — STB를 “옵션(설계 선택)”으로 유지

- 메인 스펙은 SPM과 deps_before/tag-wait만으로 엔진 협업을 표현하고,
  STB는 특정 설계에서만 사용한다.
- 장점: 메인 스펙 변경을 최소화한다.
- 단점: 엔진 간 파이프라인 경계를 표현하는 공통 어휘가 약해지고,
  통합 전 문서와의 정합성 유지 비용이 커질 수 있다.

## 4. 결정(제안)

**Option B 채택**:

- 메인 스펙은 STB를 “필수 의미론”으로 채택하되,
  구현은 물리 STB/논리 STB 중 선택 가능하게 한다.
- 따라서 “STB=물리 FIFO”로 고정하지 않고,
  “STB=타일 디스크립터 handoff 경계(ready/valid 의미론 포함)”로 정의한다.

## 5. 의미론(메인 스펙에 포함될 최소 정의)

- STB는 **타일 payload를 저장하지 않는다**.
- STB는 **타일 디스크립터(위치/shape/의존성 식별자)** 를 전달한다.
- payload는 SPM에 존재하며 엔진은 SPM을 load/store로 접근한다.
- 소비자 준비 상태에 따라 **역압(back-pressure)** 이 존재할 수 있으며,
  이는 TE→VE handoff 시점(또는 descriptor issue 시점)에서만 발생한다.

## 6. 영향 범위

- 아키텍처 규범: `docs/spec/architecture/tile_semantics_spec.md`
- 타이밍/트레이스: stall reason 분류에 “STB/descriptor back-pressure” 항목 추가 가능
- CMDQ 모델: deps_before/tag-wait가 논리적 STB의 구현 수단이 될 수 있음을 명시

## 7. 후속 작업

1) 메인 스펙에 “tile handoff 경계(=STB semantics)”를 요약본으로 추가  
2) 검증 체크리스트에 STB/descriptor 관련 항목을 포함
