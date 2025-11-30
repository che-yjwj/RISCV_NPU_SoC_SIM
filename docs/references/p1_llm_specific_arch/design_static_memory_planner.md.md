<!-- status: draft -->
# design_static_memory_planner.md
모바일 NPU용 정적 메모리 플래너 설계 문서
======================================

## 1. 목적
본 문서는 모바일 NPU 기반의 정적 스케줄링 LLM 워크로드 실행을 위해 필요한 SRAM/DRAM 메모리 배치, 타일 할당, KV 캐시 레이아웃 등을 정적으로 결정하는 메모리 플래너의 설계 사양을 정의한다.

## 2. 메모리 계층 구조
- On-chip SRAM (multi-bank)
- System DRAM
- Weight Storage Region
- KV Cache Region
- DMA 경로 및 alignment 규칙

## 3. Memory Planning 단계
1. Tensor Lifetime 분석
2. SRAM Slot 할당 및 bank mapping
3. Conflict-free 배치
4. Prefill/Decode Phase별 독립 layout 생성
5. Weight/Activation/KV 위한 정적 오프셋 계산
6. Double-buffering 영역 예약

## 4. 메모리 배치 규칙
- Activation tile은 SRAM 내부 고정 slot에 배치
- KV Cache는 DRAM의 고정된 오프셋 구조로 유지
- Weight는 압축 여부에 따라 별도 region 구성
- Prefill에서 생성된 KV 주소는 decode에서 그대로 사용
- Layer 간 activation lifetime이 겹치지 않으면 slot 재사용

## 5. Static KV Cache Layout
- Layer별 K/V base 주소
- token-index 기반 offset 계산식
- DRAM stride 규칙
- alignment 및 bank 고려

## 6. 출력물
- sram_map.json
- kv_layout.json
- bank_allocation.json
- memory_summary.txt
