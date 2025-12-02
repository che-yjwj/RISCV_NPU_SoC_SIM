# SPM Allocator Design
**Path:** `docs/design/spm_allocator_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
SPMAllocator는 TileGraph와 SPM 설정을 입력으로 받아 **각 tile의 IFM/WGT/OFM/KV 데이터를 SPM bank/offset에 배치**하는 오프라인 모듈이다.  
이 문서는 SPMAllocator의 매핑 전략과 timing/메모리 스펙과의 연계를 정의한다.

관련 스펙:
- `docs/spec/ir/tensor_metadata_spec.md`
- `docs/spec/quantization/bitwidth_memory_mapping.md`
- `docs/spec/timing/spm_model_spec.md`

## 2. 책임
- **입력**
  - TileGraph: tile 단위 shape/qbits/lifetime 정보.
  - SPM config: `num_banks`, `bank_size_bytes`, alignment 규칙 등.
- **출력**
  - 각 tile에 대해 IFM/WGT/OFM/KV별 `(bank, offset)` 매핑.
  - CMDQGenerator가 사용할 수 있는 SPM allocation 메타데이터.
- **주요 역할**
  - tile bytes를 계산하고 bank 용량 내에서 배치.
  - lifetime이 겹치지 않는 tile들을 같은 bank 공간에 재사용 가능하게 배치.
  - bank conflict를 줄이기 위한 heuristic 적용(예: 서로 다른 bank로 분산).
- **하지 말아야 할 일**
  - tile 크기/shape를 변경 (이는 TilingPlanner 책임).
  - runtime scheduling/timing 계산.

## 3. 내부 구조

### 3.1 데이터 구조
```python
class TileAllocation:
    tile_id: str
    ifm: (bank, offset, bytes)
    wgt: (bank, offset, bytes)
    ofm: (bank, offset, bytes)
    kv: Optional[(bank, offset, bytes)]
    lifetime: (start_step, end_step)
```

- `BankState[bank]`:
  - 현재 bank에 할당된 interval 목록 `(start_step, end_step, offset, size)`.

### 3.2 라이프타임 모델
- Tiling/Scheduler 단계에서 제공하는 **tile execution order**를 사용.
- 간단한 모델: `start_step = first_cmdq_id_that_uses_tile`, `end_step = last_cmdq_id_that_uses_tile`.

## 4. 알고리즘 / 플로우

### 4.1 bytes 계산
각 tensor role별로:
```text
bytes = ceil(num_elements * qbits / 8)
```
`bitwidth_memory_mapping.md`와 동일.

### 4.2 bank 할당 알고리즘(그리디 예시)
1. 타일을 라이프타임 시작 시점 기준으로 정렬.
2. 각 타일에 대해 IFM/WGT/OFM(및 KV)에 대해:
   - 각 bank에서 겹치는 interval이 없는 offset 영역을 탐색.
   - 여유 공간이 있는 bank 중 conflict 비용(예: 동일 bank에 중첩 DMA/TE 접근 수)이 최소인 bank를 선택.
3. 할당 정보를 `TileAllocation`에 기록.

```pseudo
for tile in tiles_sorted_by_start:
  for role in [IFM, WGT, OFM, KV]:
    size = bytes(tile, role)
    best_bank = argmin_bank(conflict_cost(bank, tile.lifetime, size))
    offset = first_fit_offset(bank_state[best_bank], size)
    bank_state[best_bank].add_interval(tile.lifetime, offset, size)
    record_allocation(tile.id, role, best_bank, offset, size)
```

## 5. 인터페이스
- `SpmAllocator.allocate(tile_graph, spm_config) -> Dict[tile_id, TileAllocation]`
- `SpmAllocator.dump_debug_view(path)`:
  - bank별 사용량, conflict 예상 영역을 텍스트/JSON으로 출력.

설정 파라미터:
- bank 선택 heuristic (round-robin, min-conflict, random 등).
- alignment 정책 (bank별 최소 offset 정렬 단위).

## 6. 예시 시나리오
- 작은 MLP 모델에 대한 TileGraph를 입력으로 SPMAllocator를 실행:
  - IFM/WGT가 다른 bank에 배치되어 DMA/TE 병렬성이 높아지는지,
  - bank별 사용량이 균형적인지 시각화로 검증.

### 6.1 단일 TileGraph에 대한 SPM 배치 예시

```text
SPM config:
  num_banks = 4
  bank_size_bytes = 64 KB

Tiles (간략):
  t0 (GEMM0): lifetime=[0, 3]
  t1 (GEMM1): lifetime=[1, 4]
```

예시 배치:

| Tile | Role | Bank | Offset(bytes) | Size(bytes) | Lifetime |
| --- | --- | --- | --- | --- | --- |
| t0  | IFM  | 0    | 0            | 8 KB        | [0, 3] |
| t0  | WGT  | 1    | 0            | 16 KB       | [0, 3] |
| t0  | OFM  | 2    | 0            | 8 KB        | [1, 3] |
| t1  | IFM  | 0    | 8 KB         | 8 KB        | [1, 4] |
| t1  | WGT  | 1    | 16 KB        | 16 KB       | [1, 4] |
| t1  | OFM  | 3    | 0            | 8 KB        | [2, 4] |

해석:
- t0/t1의 IFM/WGT는 서로 다른 bank 또는 다른 offset으로 배치되어 bank 충돌을 완화.
- t0의 OFM과 t1의 OFM은 lifetime이 부분적으로 겹치지 않는다면 동일 bank 내 reuse도 가능하며, allocator heuristic에 따라 선택된다.

## 7. 향후 확장
- multi-level SPM (L0/L1) 지원.
- bank 간 migration (특정 타일을 다른 bank로 재배치).
- tile lifetime을 cycle 단위로 세분화하여 더 정확한 conflict 최소화.
