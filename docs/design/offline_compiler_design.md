# Offline Compiler Design
**Path:** `docs/design/offline_compiler_design.md`
**Status:** Draft
<!-- status: in_progress -->
**Owner:** TBD
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
ONNX→CMDQ 오프라인 파이프라인 모듈/컴포넌트의 역할과 내부 구조, 확장 포인트를 정의한다.

## 2. 책임
- **입력:** ONNX 모델, 하드웨어 config
- **출력:** CMDQ, 보고용 로그/통계
- **주요 역할:** IR 변환, 타일링, 스케줄링, CMDQ 생성
- **하지 말아야 할 일:** 런타임 제어, 시뮬레이터 기능 중복

## 3. 내부 구조
- 서브모듈/클래스 개요
- 데이터 구조 또는 상태 머신
- 주요 상호작용 다이어그램 TODO

## 4. 알고리즘 / 플로우
1. 단계별 처리 요약
2. pseudo code 또는 sequence diagram TODO

## 5. 인터페이스
- 함수/메서드 시그니처(초안)
- 설정/구성 파라미터
- 관련 스펙 링크

## 6. 예시 시나리오
- 입력 → 처리 → 출력 흐름을 간단한 bullet로 설명

## 7. 향후 확장
- 추가 기능 아이디어
- 테스트/검증 전략 TODO
