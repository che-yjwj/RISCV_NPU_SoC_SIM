# Architecture Semantics Spec Index

이 디렉터리는 NPU Simulator & Offline Compiler가 공통으로 따라야 하는
**아키텍처 실행 의미론(semantics)** 을 정의한다.

## 문서 목록

- `stb_adoption_rfc.md` — STB(Shared Tile Buffer) 의미론/채택 범위 결정(RFC)
- `tile_semantics_spec.md` — Tile 라이프사이클/메모리 계층/TE–VE 데이터플로우의 최소 불변 규칙
- `kv_cache_semantics_spec.md` — LLM KV cache의 타일링/상주/재사용 의미론(Decode streaming 규칙 포함)
- `tile_contract_spec.md` — HW–SW 경계 계약(타일 단위 원자성/메모리 경계/결정론 요구사항)

## 적용 범위

- 메인 스펙(`docs/spec/*`)을 기준으로 한다.
- 규범은 메인 스펙을 단일 소스 오브 트루스로 삼는다.
