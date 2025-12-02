# CMDQ Generator Design
**Path:** `docs/design/cmdq_generator_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

---

## 1. 목적
CmdqGenerator는 StaticScheduler와 SPMAllocator의 결과를 사용해 **CMDQ JSON**을 생성하는 모듈이다.  
이 문서는 tile-level ScheduleDAG → CMDQ 엔트리 매핑 규칙과 JSON 구조를 정의한다.

관련 스펙:
- `docs/spec/isa/cmdq_overview.md`
- `docs/spec/isa/cmdq_format_spec.md`

## 2. 책임
- **입력**
  - ScheduleDAG (tile-level 엔트리, deps, engine assignment).
  - SPM allocation 정보 (bank/offset).
  - NPU IR / Tensor metadata (layer_id, tensor_role, qbits 등).
- **출력**
  - CMDQ JSON (`cmdq` 리스트 + `metadata` 블록).
- **주요 역할**
  - ScheduleEntry를 CMDQ entry로 1:1 혹은 1:N 매핑.
  - deps_before를 CMDQ index 기반 배열로 변환.
  - trace/디버깅에 유용한 debug 메타데이터 추가.
- **하지 말아야 할 일**
  - 스케줄 자체 수정 (순서/엔진 배치 변경).
  - 타이밍/성능 계산.

## 3. 내부 구조

### 3.1 CmdqEntryBuilder
```python
class CmdqEntryBuilder:
    def from_schedule_entry(entry, spm_alloc, ir) -> dict:
        ...
```

### 3.2 Id/Index 매핑
- ScheduleDAG는 내부 id를 가지고 있으며, CMDQ 인덱스로 재부여:
  - `cmdq_index_map[schedule_entry.id] = idx`
- deps_before는 이 매핑을 사용해 CMDQ index 배열로 변환.

## 4. 알고리즘 / 플로우

### 4.1 엔트리 생성
```pseudo
cmdq = []
for entry in schedule.entries_in_execution_order():
    cmdq_entry = build_cmdq_entry(entry, spm_alloc, ir)
    cmdq_entry.id = len(cmdq)
    cmdq.append(cmdq_entry)
```

### 4.2 deps 매핑
```pseudo
for e in schedule.entries:
    cmdq_id = cmdq_index_map[e.id]
    cmdq[cmdq_id].deps_before = [
        cmdq_index_map[d] for d in e.deps_before
    ]
```

### 4.3 opcode별 필드 채우기
- DMA:
  - `opcode`: `DMA_LOAD_TILE` / `DMA_STORE_TILE`
  - `tensor_role`, `qbits`, `dram_addr`, `spm_bank`, `spm_offset`, `num_elements`
- TE:
  - `opcode`: `TE_GEMM_TILE`
  - `te_id`, `ifm_bank`, `wgt_bank`, `ofm_bank`, `m`, `n`, `k`, `qbits_*`
- VE:
  - `opcode`: `VE_*_TILE`
  - `ve_id`, `length`, `qbits_activation`, 추가 attr.

### 4.4 Mini Golden CMDQ 예시

아래는 단일 GEMM + LayerNorm 레이어에 대한 Schedule → CMDQ 매핑 예시이다.

```text
Schedule entries (id, type, deps_before):
  e0: DMA_LOAD_IFM   deps=[]
  e1: DMA_LOAD_WGT   deps=[]
  e2: TE_GEMM_TILE   deps=[e0, e1]
  e3: VE_LAYERNORM   deps=[e2]
  e4: DMA_STORE_OFM  deps=[e3]
```

CmdqGenerator 결과 (요약):

```json
{
  "cmdq": [
    { "opcode": "DMA_LOAD_TILE",   "id": 0, "layer_id": "ffn_0", "deps_before": [] },
    { "opcode": "DMA_LOAD_TILE",   "id": 1, "layer_id": "ffn_0", "deps_before": [] },
    { "opcode": "TE_GEMM_TILE",    "id": 2, "layer_id": "ffn_0", "deps_before": [0, 1] },
    { "opcode": "VE_LAYERNORM_TILE","id": 3,"layer_id": "ffn_0_ln","deps_before": [2] },
    { "opcode": "DMA_STORE_TILE",  "id": 4, "layer_id": "ffn_0", "deps_before": [3] },
    { "opcode": "END",             "id": 5, "layer_id": null,    "deps_before": [4] }
  ]
}
```

이 예시는 다음을 보여 준다.
- Schedule entry id → CMDQ `id` 재부여 및 `deps_before` 인덱스 매핑.
- IR의 `layer_id`가 CMDQ 엔트리에 보존되어 trace와 join할 수 있음.
- 마지막 `END` 엔트리는 StaticScheduler가 생성하거나, CmdqGenerator가 tail에 자동 추가할 수 있다(구현 선택 사항).

## 5. 인터페이스
- `CmdqGenerator.generate(schedule, spm_alloc, ir, config) -> CmdqArtifact`
  - `CmdqArtifact`에는 CMDQ JSON과 부가 메타(`graph_name`, `version`, `generated_by`)를 포함.

구성 파라미터:
- debug flag (추가 필드 포함 여부).
- CMDQ version/tag.

## 6. 예시 시나리오
- 단일 레이어 스케줄에 대해:
  - ScheduleDAG를 입력으로 CMDQ를 생성하고,  
    각 CMDQ 엔트리의 deps_before가 스케줄 의존성과 정확히 일치하는지 검사.

## 7. 향후 확장
- binary CMDQ 포맷 생성 (JSON→binary encoder).
- CMDQ 최적화(pass) 훅 (엔트리 merge, reorder 등) 추가.
