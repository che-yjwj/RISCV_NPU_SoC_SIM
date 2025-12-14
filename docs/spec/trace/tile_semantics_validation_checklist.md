# Tile Semantics Validation Checklist (SPM / Lifecycle / STB)

**Version:** v1.0  
**Status:** Draft  
<!-- status: draft -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-14

관련 스펙:
- 아키텍처 의미론: `docs/spec/architecture/tile_semantics_spec.md`
- STB 채택 RFC: `docs/spec/architecture/stb_adoption_rfc.md`
- SPM 타이밍/충돌 모델: `docs/spec/timing/spm_model_spec.md`
- Trace 포맷: `docs/spec/trace/trace_format_spec.md`

## 1. Tile 라이프사이클 검증

- [ ] allocate 이전에 tile을 consume/load 대상으로 사용하지 않는다.
- [ ] produce 이전에 handoff(디스크립터 전달)를 발생시키지 않는다.
- [ ] STB(또는 논리적 handoff 경계)가 참조 중인 타일은 free되지 않는다.
- [ ] consume 중(또는 예정)인 타일은 free되지 않는다.
- [ ] free는 명시적 이벤트로 기록되며, 스케줄러 관점에서 결정적이다.

권고 trace 필드:
- tile_id, state_transition(allocated/produced/handedoff/consumed/freed), cycle

## 2. SPM(=tile payload 저장소) 검증

- [ ] 타일 payload는 SPM에만 존재하며, 엔진은 SPM을 load/store로만 접근한다.
- [ ] SPM 용량(바이트/타일 수)을 초과하면 stall 또는 실패로 처리한다.
- [ ] bank/port conflict 판정은 `spm_model_spec.md`의 주소 매핑 규칙과 일치한다.

권고 trace 필드:
- spm_access_events(cycle, bank, bytes, requester, conflict)
- spm_occupancy(cycle, bytes, peak_bytes)

## 3. STB(디스크립터 handoff 경계) 검증

STB는 물리 FIFO일 수도 있고, CMDQ deps_before/tag-wait로 구현된 논리 경계일 수도 있다.

- [ ] STB에는 payload가 존재하지 않는다(디스크립터만).
- [ ] TE→VE 경로에서 “최초 소비”는 최소 1회 handoff 경계를 거친다.
- [ ] back-pressure(소비자 준비 불가)는 handoff 경계에서만 모델링된다.

권고 trace 필드:
- stb_push(tile_id, cycle), stb_pop(tile_id, cycle)
- stall_reason에 `stb_backpressure` 또는 동등 분류 포함

## 4. DRAM 사용 검증(중간 결과 금지)

- [ ] 중간 결과 타일을 DRAM에 저장하여 엔진 간 전달에 사용하지 않는다.
- [ ] DRAM 접근은 DMA(또는 명시적 전송 노드)로만 표현된다.
- [ ] KV cache는 “장기 입력 데이터”로 DRAM 영속 저장이 허용되며, Decode에서는 Time_tile 단위로 staging한다.

권고 trace 필드:
- dram_bytes_read/write per op/tile, KV 관련 role 표기(optional)

## 5. 최소 회귀(Regression) 체크

아래 예제 문서들은 위 규칙의 빠른 회귀 기준으로 사용 가능하다.

- `docs/test/examples/pytorchsim_npu_ir_examples.md`
- `docs/test/examples/tutorial_minimal_llama_to_tile_npu.md`
