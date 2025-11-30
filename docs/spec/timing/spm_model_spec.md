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

## 2. 하드웨어 파라미터
- `num_banks`, `bank_size_bytes`
- `read_ports`, `write_ports`, `dual_port`
- `bank_width_bytes` (address increment 기준)
- `access_latency_cycles`
- `conflict_penalty_cycles`

## 3. 주소 매핑 규칙
```
bank_index = (address / bank_width_bytes) % num_banks
offset_in_bank = address % bank_size_bytes
```
SPMAllocator는 bank/offset을 계산하여 CMDQ에 기록하며, 시뮬레이터는 동일 공식을 사용해 충돌 여부를 판정한다.

## 4. 충돌 모델
1. **Port 한계:** 동일 cycle에 동일 bank에 read/write 수가 포트 수를 초과하면 stall 발생.
2. **Bank conflict penalty:** 초과 요청은 `conflict_penalty_cycles`만큼 대기 후 재시도.
3. **DMA vs TE/VE arbitration:** DMA가 우선권을 가지되 starvation 방지를 위해 max_wait_cycles 이후 공평 배분.

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
