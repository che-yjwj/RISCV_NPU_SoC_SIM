# Architecture Semantics Spec Index

이 디렉터리는 NPU Simulator & Offline Compiler가 공통으로 따라야 하는
**아키텍처 실행 의미론(semantics)** 을 정의한다.

## 문서 목록

- `stb_adoption_rfc.md` — STB(Shared Tile Buffer) 의미론/채택 범위 결정(RFC)
- `tile_semantics_spec.md` — Tile 라이프사이클/메모리 계층/TE–VE 데이터플로우의 최소 불변 규칙

## 적용 범위

- 메인 스펙(`docs/spec/*`)을 기준으로 한다.
- `docs/tile_based/`는 참고/실험 트랙이며, 규범은 메인 스펙을 단일 소스 오브 트루스로 삼는다.
