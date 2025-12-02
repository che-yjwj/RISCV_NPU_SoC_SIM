# Visualization Requirements
**Path:** `docs/spec/trace/visualization_requirements.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
Trace 데이터를 활용하는 시각화 도구가 제공해야 할 필수 뷰, 인터랙션, 내보내기 기능을 정의한다.

## 2. 필수 뷰
1. **Gantt Timeline:** 엔진별 실행 상태.
2. **Bandwidth Heatmap:** DRAM/Bus 사용률.
3. **Engine Utilization Dashboard:** DMA/TE/VE busy %, idle/stall 구간.
4. **Quantization Impact Plot:** qbits 별 latency/bytes 변화 비교.

## 3. 입력 포맷
- 기본 입력: `trace_format_spec.md` JSON.
- 옵션 입력: CMDQ snapshot, IR metadata.

## 4. UX 요구사항
- 범위 필터(레이어/토큰/엔진).
- Bookmark/annotation 기능.
- 비교 모드: 두 trace를 나란히 보여 latency 차이 강조.

## 5. Export/Automation
- PNG/SVG/CSV 내보내기.
- CLI 모드에서 batch 렌더 지원.
- Notebook/API 연동을 위한 Python 바인딩 권장.

## 6. 성능 가이드
- 1M events 이상 처리 가능해야 함.
- Level-of-detail 렌더링으로 확대/축소 시 성능 유지.

## 7. 향후 확장
- Live streaming trace 뷰어.
- Web 기반 대시보드.
