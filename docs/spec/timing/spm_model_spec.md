# SPM Model Specification
**Path:** `docs/spec/timing/spm_model_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Memory Architect  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
SPM(Scratchpad Memory)의 bank/port 구조, 주소 매핑, 충돌 모델을 정의해 DMA/TE/VE가 일관된 용량과 대역폭 제약을 사용하도록 한다.

관련 문서:
- 아키텍처 의미론(타일 라이프사이클/메모리/데이터플로우): `docs/spec/architecture/tile_semantics_spec.md`
- STB(디스크립터 handoff 경계) 채택 범위: `docs/spec/architecture/stb_adoption_rfc.md`
- 결정론적 중재(버스/NoC): `docs/spec/timing/bus_and_noc_model.md`

## 1.1 결정론 규칙(필수)

SPM 충돌/중재는 사이클 기반으로 모델링하되, 동일 입력이면 항상 동일 결과가 나와야 한다.

- 랜덤/RNG/seed 기반 중재 금지
- 동률(tie) 발생 시 tie-break 규칙 고정
- 요청 수집/처리 순서 고정(아래 4절 참고)

## 2. 하드웨어 파라미터
- `num_banks`, `bank_size_bytes`
- `read_ports`, `write_ports`, `dual_port`
- `bank_width_bytes` (address increment 기준)
- `access_latency_cycles`
- `conflict_penalty_cycles`
- `max_wait_cycles` (starvation 방지용, 선택)
- `tie_break` (동률 처리 규칙, 필수)

### 2.1 Requester ID & Ordering (결정론)

SPM 접근 요청은 다음 필드를 가진다고 가정한다.

- `requester_type`: `DMA | TE | VE`
- `requester_id`: `int` (requester_type 내에서 유일)

결정론을 위한 전역 정렬 키:

```text
requester_key = (type_rank(requester_type), requester_id)
type_rank: DMA=0, TE=1, VE=2
```

이 문서에서 `requester_id` 오름차순이라 함은 `requester_key` 기준 오름차순을 의미한다.

ID 매핑(권고):

- `requester_type=DMA`의 `requester_id`는 CMDQ 엔트리의 `dma_id`를 사용한다.
- `requester_type=TE`의 `requester_id`는 `te_id`, `requester_type=VE`의 `requester_id`는 `ve_id`를 사용한다.

## 3. 주소 매핑 규칙
```
bank_index = (address / bank_width_bytes) % num_banks
offset_in_bank = address % bank_size_bytes
```
SPMAllocator는 bank/offset을 계산하여 CMDQ에 기록하며, 시뮬레이터는 동일 공식을 사용해 충돌 여부를 판정한다.

## 4. 충돌 모델
1. **Port 한계:** 동일 cycle에 동일 bank에 read/write 수가 포트 수를 초과하면 stall 발생.
2. **Bank conflict penalty:** 초과 요청은 `conflict_penalty_cycles`만큼 대기 후 재시도.
3. **DMA vs TE/VE arbitration(결정론):** 아래 규칙을 따른다.
   - 기본 우선순위: DMA > TE > VE
   - 동일 우선순위 내 tie-break: `requester_key` 오름차순
   - starvation 방지(권고): `max_wait_cycles`를 두고 초과 시 round-robin으로 승격(grant)하되, 승격 순서도 `requester_id` 오름차순으로 고정한다.

## 5. Allocate/Free 수명주기
- Tile별 IFM/WGT/OFM bank 점유 기간: DMA load 완료 → TE/VE 소비 종료 → DMA store 완료 시 해제.
- SPMAllocator는 lifetime 겹침을 피하도록 schedule 정보 기반으로 배치.

## 6. Validation 체크
- bank/offset이 용량 범위 내인지 확인.
- overlapping tiles가 동일 bank 영역을 점유하지 않는지 정적 검사.
- 시뮬레이터는 런타임에 out-of-range 접근 시 오류/trace 이벤트 기록.

## 7. Trace Hooks
- `spm_access_events`: cycle, bank, bytes, requester(DMA/TE/VE), conflict 여부.
- `spm_bank_utilization`: window별 bank 사용률.

## 8. 확장성
- Multi-layer SPM (L0/L1) 추가 시 동일 규칙 반복 적용.
- ECC/Parity, compression buffer 등 특수 bank 정의 가능.
- Future work: per-bank voltage/frequency scaling 모델.
