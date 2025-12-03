# Visualizer Design
**Path:** `docs/design/visualizer_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
Visualizer는 시뮬레이터가 생성한 Trace JSON과 부가 메타데이터를 입력으로 받아  
**Gantt Timeline, Bandwidth Heatmap, Utilization Dashboard, Quantization Impact Plot** 등을 생성하는 모듈이다.  
이 문서는 Visualizer의 서브모듈, 데이터 플로우, 확장 포인트를 정의한다.

관련 스펙:
- `docs/spec/trace/trace_format_spec.md`
- `docs/spec/trace/gantt_timeline_spec.md`
- `docs/spec/trace/bandwidth_heatmap_spec.md`
- `docs/spec/trace/visualization_requirements.md`

## 2. 책임
- **입력**
  - Trace JSON (`trace_format_spec.md` 준수).  
  - Optional: IR/TileGraph/CMDQ snapshot (추가 레이블링용).  
- **출력**
  - 시각화 결과: 이미지(SVG/PNG), 대화형 HTML, 요약 표/CSV.  
  - 분석 데이터: layer별 latency breakdown, engine utilization, peak bandwidth 등.
- **주요 역할**
  - Trace를 파싱하고, 분석-friendly한 내부 표현으로 정규화.  
  - 다양한 뷰를 생성하는 렌더 파이프라인 제공.  
- **하지 말아야 할 일**
  - CMDQ/Trace 포맷 변경(스펙 위반).  
  - 시뮬레이터 실행/타이밍 자체를 변경.

## 3. 내부 구조

### 3.1 서브모듈
- `TraceLoader`
  - Trace JSON을 로드하고, 버전/스키마 검증 수행.  
- `TimelineModel`
  - ENGINE_EVENT를 가공해 Gantt에 적합한 구조로 변환.  
- `BandwidthModel`
  - bandwidth_samples를 Heatmap용 그리드로 변환.  
- `UtilizationModel`
  - summary_metrics와 timeline을 사용해 엔진별 utilization 계산.  
- `Renderer`
  - Gantt/Heatmap/Chart를 실제 SVG/PNG/HTML로 생성하는 모듈.

### 3.2 데이터 구조 (예시)
```python
class EngineSpan:
    engine: str
    engine_id: int
    cmdq_id: int
    layer_id: str
    start: int
    end: int
    op: str
```

```python
class BandwidthSample:
    start_cycle: int
    window_cycles: int
    read_bytes: int
    write_bytes: int
    utilization: float
```

## 4. 알고리즘 / 플로우

### 4.1 기본 파이프라인
```pseudo
trace = TraceLoader.load(path)
timeline = TimelineModel.from_trace(trace)
bw_grid = BandwidthModel.from_trace(trace)
util = UtilizationModel.from_trace(trace)

Renderer.render_gantt(timeline, output_gantt_path)
Renderer.render_bandwidth_heatmap(bw_grid, output_bw_path)
Renderer.render_utilization(util, output_util_path)
```

### 4.2 Gantt 렌더링 개략
- TimelineModel:
  - ENGINE_EVENT들을 엔진별로 그룹화.  
  - cycle 범위를 X축, 엔진 lane을 Y축으로 매핑.  
- Renderer:
  - 각 span을 사각형으로 그리되, 색상은 `engine`/`op`에 따라 결정.  
  - deps나 토큰 경계는 별도 오버레이로 표현.

### 4.3 Heatmap 렌더링 개략
- BandwidthModel:
  - window별 `utilization`을 계산.  
  - X축=시간, Y축=metric(read/write/total 또는 channel).  
- Renderer:
  - 컬러맵(예: 0~1 → 파란색~빨간색)을 사용해 표 형태로 그린다.

### 4.4 뷰 구성 개략 다이어그램

```text
Trace JSON
   |
   v
[TraceLoader] --> [TimelineModel]  -->  Gantt Timeline (MVP)
             \-> [BandwidthModel] -->  Bandwidth Heatmap (MVP)
             \-> [UtilizationModel] --> Engine Util Dashboard (MVP)
             \-> [QuantizationModel?] --> Quantization Impact Plot (확장)
```

- MVP: Gantt, BW Heatmap, Utilization Dashboard.
- 확장: Quantization Impact Plot, multi-run diff view, 대화형 웹 UI.

## 5. 인터페이스
- 라이브러리 스타일 예시:
  - `visualizer.render_all(trace_path, output_dir, config)`  
  - 개별 뷰:
    - `render_gantt(trace_path, out_path)`  
    - `render_bandwidth_heatmap(trace_path, out_path)`  
    - `render_utilization(trace_path, out_path)`  

## 6. 튜토리얼: Trace 생성 → Golden 비교 → 시각화

아래는 처음 보는 사람이 따라 할 수 있는 최소 워크플로우 예시이다.

1. **Trace 생성**  
   - Integration 테스트(예: IT-MLP-01)나 Performance 검증(PV-LLM-01)을 실행해 Trace JSON을 생성한다.  
   - 출력 위치는 보통 `tests/artifacts/trace/<name>.json` 또는 설정된 output 디렉터리이다.
2. **Golden 비교 (선택)**  
   - `docs/test/golden_trace_examples.md`에서 대응하는 Golden ID(GT-MLP-01 등)를 찾고, golden trace 경로를 확인한다.  
   - 회귀 테스트(예: `tests/regression/test_golden_trace.py`)나 간단한 비교 스크립트로 현재 Trace와 golden trace를 비교한다.
3. **시각화 실행**  
   - Visualizer 라이브러리/CLI에서:
     - `visualizer.render_all("tests/artifacts/trace/mlp_run.json", "out/vis/mlp_run/", config)`  
   - 또는 개별 뷰를 호출:
     - `render_gantt`, `render_bandwidth_heatmap`, `render_utilization` 등.
4. **분석 포인트**  
   - Gantt: TE/VE/DMA 타임라인이 Dataflow/Design 문서와 일치하는지 확인.  
   - Bandwidth Heatmap: DRAM traffic 패턴이 Timing/Memory 스펙에서 예상한 범위인지 확인.  
   - Utilization: 병목 엔진(TE/VE/DMA)을 식별하고, 타일링/스케줄 변경 아이디어를 얻는다.

자세한 trace 필드 정의는 `trace_format_spec.md`,  
Golden trace 구성은 `golden_trace_examples.md`를 함께 참고한다.
- 설정/파라미터:
  - 시간 범위, 레이어/엔진 필터, 색상 테마, 출력 포맷(SVG/PNG/HTML/CSV).

## 6. 예시 시나리오
- LLM Prefill/Decode trace를 입력으로:
  - Gantt에서 TE/VE/DMA의 중첩 구간을 확인.  
  - Heatmap에서 KV Cache 구간의 DRAM BW spike 확인.  
  - Utilization chart에서 엔진별 병목 지점을 찾는다.

## 7. 향후 확장
- 대화형 웹 UI(줌/필터/툴팁) 연동.  
- 여러 run(trace)을 비교하는 diff view (before/after optimization).  
- 자동 레포트 생성(HTML/PDF) 기능 추가.  
