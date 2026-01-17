# 작 업 목 적

본 작업의 목적은 기존 파일 기반 프롬프트와 신규 DB 기반 Prompt Asset을 병행 운영하면서 발생할 수 있는 혼란을 방지하고 개발/운영/AI 개선(Codex 활용) 모두가 같은 기준으로 작업하도록 지침을 고정하는 것이다.

---

## 1️⃣ 개요 (Why)

### 1.1 배경

기존 프롬프트는 `resources/prompts/**/*.yaml` 파일 기반으로 관리되었으며 예전부터 개발/작업용의 기준 역할을 담당했다. 운영 UI(Assets)가 도입되면서 Prompt Asset(DB)이 추가되어 개발과 운영이 각각 다른 저장소를 참고하는 전환기 상태가 되었다. 이 문서는 두 체계가 공존하는 동안 혼란이 생기지 않도록 정본을 명확히 정의하고, 운영·개선 모두 동일한 기준으로 작업되도록 안내한다.

### 1.2 목표

1. 운영 중 프롬프트의 정본(source of truth)을 Prompt Asset(DB)으로 고정한다.  
2. Codex/AI 개선 작업이 기존 흐름을 방해하지 않고 계속 가능하도록 보장한다.  
3. 납품(오프라인) 환경에서도 복구 및 이해가 가능하도록 File Prompt를 Seed·문서·백업용으로 유지한다.

## 2️⃣ 용어 정의 (중요)

| 용어 | 정의 |
| --- | --- |
| **File Prompt** | 현재 저장소의 `resources/prompts` 이하에 존재하는 YAML 프롬프트 |
| **Prompt Asset** | Asset Registry(DB)에 저장된 프롬프트 |
| **Seed Prompt** | 최초 기준이 되는 File Prompt |
| **Published Prompt** | 운영에 실제 적용 중인 Prompt Asset |
| **Fallback** | Prompt Asset이 없을 때 File Prompt를 사용하는 동작 |

## 3️⃣ 기본 운영 원칙 (가장 중요)

### 3.1 단일 정본 원칙

운영 시점의 정본은 Prompt Asset(DB)이며, File Prompt는 Seed, 백업, 문서로서의 역할만 담당한다.

### 3.2 병행 운영 원칙

개발 단계에서는 File Prompt와 Prompt Asset을 병행 유지한다. 운영 변경은 반드시 Prompt Asset을 통해서만 수행하고, File Prompt 직접 수정은 제외한다.

### 3.3 Codex/AI 개선 원칙

Codex는 File Prompt 또는 Export된 Prompt Asset 텍스트를 기준으로 개선 작업을 실시한다. Codex가 DB를 직접 수정하는 것은 불가능하며, 항상 사람(운영자/개발자)이 개선안을 Prompt Asset UI에 반영한다.

## 4️⃣ Prompt의 생명주기 (Lifecycle)

```
[File Prompt (Seed)]
        |
        |  (1회 Import)
        v
[Prompt Asset - Draft]
        |
        |  Publish
        v
[Prompt Asset - Published]
        |
        |  Rollback
        v
[New Draft (from previous version)]
```

* File Prompt는 자동으로 Asset으로 변환되지 않으며 최초 1회만 수동 Import한다.

## 5️⃣ 개발 단계 작업 규칙

### 5.1 프롬프트 개선 작업 시

1. Codex에게 File Prompt 또는 Export된 Prompt Asset 텍스트를 제공하여 분석·개선 제안을 받는다.  
2. 개선안 검토 후 필요하다면 File Prompt를 업데이트한다(선택).  
3. 운영 적용을 위한 최종 내용은 Prompt Asset UI에 반영한다.

### 5.2 금지 사항

* DB Prompt Asset 내용을 레포에 없는 상태로 방치하지 않는다.  
* 어떤 프롬프트가 운영 중인지 모르는 상태에서 수정하지 않는다.  
* File Prompt와 Prompt Asset을 동기화되지 않은 채로 혼용하지 않는다.

* 최초 일회 이관은 `scripts/prompt_asset_importer.py`를 활용한다. 기본 `--scope ci` 플래그로 `resources/prompts/ci/*.yaml`을 순회하고, API 서버가 실행 중일 때 `--apply --publish`를 함께 사용하면 Draft 생성과 Publish를 자동으로 수행한다. File Prompt는 그대로 두고, Export된 내용을 `content`/`template` 필드로 넘겨 Prompt Asset을 등록한다. 이 스크립트는 `planner`/`langgraph` 둘 중 하나만 허용하는 Validator를 우회하기 위해, `ci` scope에서는 engine을 `planner`로, `ops` scope에서는 `langgraph`로 자동 지정한다.
* 이미 Draft가 존재하는 경우 `--cleanup-drafts` 를 사용하면 사전 삭제 후 새 Draft를 만들고 Publish할 수 있다. Delete API(`DELETE /asset-registry/assets/{asset_id}`)는 Draft에 대해서만 열려 있으므로 운영 중인 Publish 자산은 영향을 받지 않는다. 롤백은 `POST /asset-registry/assets/{asset_id}/rollback?to_version={n}`을 호출하면 됩니다.

## 6️⃣ 운영 단계 작업 규칙

### 6.1 운영 중 변경

운영 변경은 반드시 Assets UI의 Prompt Asset에서만 수행하며, File Prompt를 직접 수정하지 않는다.

### 6.2 장애 대응

1. Inspector로 적용된 Prompt Asset 버전을 확인한다.  
2. 필요 시 Rollback을 수행하고, File Prompt는 복구 수단으로만 사용한다.

## 7️⃣ Codex/LLM 활용 가이드 (중요)

**Codex가 할 수 있는 것**

- 프롬프트 텍스트 분석  
- 개선 제안  
- 구조/출력 계약 개선

**Codex가 할 수 없는 것**

- DB 직접 접근  
- Prompt Asset 자동 수정

**권장 흐름**

1. 운영 Prompt Export  
2. Codex 분석/개선  
3. 사람 검토  
4. Asset UI 반영

## 8️⃣ FAQ (반드시 포함)

**Q. File Prompt를 삭제해도 되나요?**  
A. ❌ 안 됩니다. Seed/백업/문서 역할을 하기 때문에 유지해야 한다.

**Q. Codex는 DB Prompt를 못 보는데 문제 없나요?**  
A. ❌ 문제 없습니다. Export 또는 File Prompt를 기준으로 작업하면 된다.

**Q. 운영 중 Prompt가 뭔지 헷갈리면?**  
A. Assets UI의 Published Prompt가 정답이다.

## 9️⃣ 책임과 권한

| 역할 | 책임 |
| --- | --- |
| **개발자** | Seed Prompt 유지, Import 도구 관리 |
| **운영자** | Prompt Asset 관리/Publish/Rollback |
| **AI 개선 담당** | Codex 활용 개선안 제시 |

## 3. 작업 완료 기준 (DoD)

1. `PROMPT_ASSET_OPERATION_GUIDE.md` 생성  
2. 위 구조를 모두 포함  
3. 팀 내 공유 및 “운영 기준 문서”로 합의  
4. 이후 모든 Prompt 관련 작업은 이 문서를 기준으로 수행

## 4. 다음 단계 (이 문서 완료 후에만 진행)

1. 기존 File Prompt → Prompt Asset 1회 이관  
2. Planner의 Asset 우선 로딩 로직 패치  
3. (선택) Prompt Export 기능 또는 UI copy 가이드

## 마지막으로 한 문장 요약

Prompt는 이제 코드가 아니라 운영 자산이다. File은 기준이고, DB는 정본이며, Codex는 조언자다.
