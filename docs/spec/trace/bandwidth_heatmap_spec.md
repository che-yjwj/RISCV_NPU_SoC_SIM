# Bandwidth Heatmap Specification
**Path:** `docs/spec/trace/bandwidth_heatmap_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
DRAM/Bus 대역폭 사용률을 시간축 heatmap으로 표현하기 위한 데이터 포맷과 렌더링 규칙을 정의한다.

## 2. 입력 데이터
`trace_format_spec.md`의 `bandwidth_samples` 배열을 사용한다.
필드: `cycle`, `window_cycles`, `dram_read_bytes`, `dram_write_bytes`, (옵션)`kv_bytes`.

## 3. 파생 메트릭
```
read_bw = dram_read_bytes / window_cycles
write_bw = dram_write_bytes / window_cycles
total_bw = read_bw + write_bw
utilization = total_bw / peak_bw_bytes_per_cycle
```
Peak BW는 `config_snapshot.memory`에서 취득.

## 4. Heatmap 구성
- X축: 시간(window).
- Y축: 채널 또는 metric (read/write/total).
- 색상 스케일: 0→peak_bw, linear 혹은 log 선택.
- Threshold 표시: utilization > 0.8 시 경고 표시.

### 4.1 예시 샘플

```json
"bandwidth_samples": [
  {
    "cycle": 1000,
    "window_cycles": 64,
    "dram_read_bytes": 4096,
    "dram_write_bytes": 1024,
    "kv_bytes": 2048
  },
  {
    "cycle": 1064,
    "window_cycles": 64,
    "dram_read_bytes": 2048,
    "dram_write_bytes": 0,
    "kv_bytes": 2048
  }
]
```

이 두 샘플을 기반으로 viewer는:
- window별 read/write/total BW를 계산하고,
- `kv_bytes`를 별도 채널로 표시해 KV cache traffic hotspot을 시각화할 수 있다.

## 5. 추가 기능
- Token boundary/레이어 boundary overlay.
- 특정 채널/role(KV) 필터링.
- CSV/PNG export.

## 6. Validation
- window가 서로 겹치지 않거나, 겹친 경우 중복 여부 명시.
- 음수 bytes 금지.
- `window_cycles > 0` 확인.

## 7. 향후 확장
- Per-bank/NoC 링크 heatmap.
- Energy per byte 추정치 포함.
