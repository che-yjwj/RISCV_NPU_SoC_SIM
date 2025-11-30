# Gantt Timeline Specification
**Path:** `docs/spec/trace/gantt_timeline_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Trace/Visualization Architect  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
시뮬레이터 타임라인 이벤트를 Gantt 차트로 시각화하기 위한 필드, 렌더링 규칙, 검증 절차를 정의한다.

## 2. 이벤트 구조
- 입력: `trace_format_spec.md`의 `ENGINE_EVENT`.
- 필수 필드: `engine`, `engine_id`, `cmdq_id`, `layer_id`, `tile_id`, `start_cycle`, `end_cycle`.
- 옵션 필드: `deps`, `color_hint`, `quantization_bits`, `notes`.

## 3. 시각화 규칙
| 항목 | 규칙 |
|------|------|
| 축 | X축=cycle, Y축=engine lane |
| 색상 | 엔진 타입별 기본 팔레트 (DMA=blue, TE=green, VE=orange, CTRL=gray) |
| 겹침 | 동일 엔진에서 겹치는 이벤트는 스택 표시, idle 구간은 연한 회색 |
| 주석 | deps/토큰 구간은 상단 마커로 강조 |

## 4. 데이터 파이프라인
```
trace.json → timeline normalizer → (optional) filtering/grouping → renderer
```
CLI/GUI 모두 JSON→SVG/PNG/HTML export를 지원.

## 5. Validation
- `start_cycle <= end_cycle`.
- Gantt 범위는 trace summary `cycles_total`을 초과하지 않아야 함.
- CMDQ id가 timeline 시퀀스에 존재하는지 확인.

## 6. 인터랙션 요구사항(옵션)
- 범위 선택/줌, 엔진/레이어 필터, 토큰 경계 jump.

## 7. 향후 확장
- stall 이벤트 오버레이.
- multi-node 동기화 선 표현.
- hot path 자동 강조.
