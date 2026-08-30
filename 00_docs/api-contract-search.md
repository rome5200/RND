# `/api/search` 응답 스키마 계약 (v1)

- 대상: `03_webapp/backend/main.py`의 `GET /api/search`
- 상태: **A.1 안정화 기준선(baseline)**. A.2/A.3 등 이후 트랙은 이 문서를 계약으로 삼아 병렬 착수한다.
- 원칙: **v1의 기존 키는 의미·타입을 바꾸지 않는다.** 새 기능은 새 top-level 키만 추가한다(§7).
- 근거 코드: `backend/pipeline.py`(`search_similar_tasks`, `recommend_researchers`), `backend/main.py`(`get_search`).

---

## 1. 요청 (Query parameters)

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `query` | string | `""` | 준비 중인 과제 주제(자유 텍스트). 공백만/빈 문자열이면 `blank_query` 상태. |
| `threshold` | float | `0.15` (`SIMILARITY_THRESHOLD`) | 유사 매칭 임계값. TF-IDF·임베딩 결합 유사도가 이 값 이상이면 매칭. |
| `rank_by` | enum string | `"최고 유사도"` | 연구자 추천 정렬 기준. 허용값: `최고 유사도` / `유사 과제 건수` / `합산 점수` (`RANK_OPTIONS`). 그 외 값은 기본값처럼 처리. |

유사도 결합 규칙(참고, 계약 대상 아님): `max(TF-IDF 코사인, 게이팅된 임베딩 코사인)`. 임베딩은 `EMBEDDING_SIMILARITY_THRESHOLD=0.6` 미만이면 0으로 눌러 반영 안 함.

---

## 2. 상태 판별 (4개 상태)

응답은 아래 4개 상태 중 정확히 하나다. **`status` 필드(§3)를 유일한 판별자로 사용할 것** — 여러 boolean 조합으로 추론하지 말 것.

| status | 발생 조건 | tasks | researchers |
|---|---|---|---|
| `ok` | query 정상 · 코퍼스 > 0 · 매칭 ≥ 1 | 유사도 상위 `TOP_N_TASKS`(=5) | 상위 `TOP_N_RESEARCHERS`(=5) |
| `reference_only` | query 정상 · 코퍼스 > 0 · 매칭 0 | 참고용 상위 3건 | 참고용 상위 3명 |
| `blank_query` | `query`가 빈 문자열/공백만 | `[]` | `[]` |
| `empty_corpus` | 매칭 대상 데이터 0건(방어적, 실데이터에선 미발생) | `[]` | `[]` |

---

## 3. 응답 envelope (모든 상태 공통)

**모든 상태에서 아래 키가 항상 존재한다**(값이 없으면 `null`/`0`/`[]`). 이것이 A.1 안정화의 핵심 — 상태에 따라 키가 사라지지 않는다.

| 키 | 타입 | 상태별 값 | 설명 |
|---|---|---|---|
| `status` | enum string | 4개 중 1 | 유일한 판별자. `ok`/`reference_only`/`blank_query`/`empty_corpus`. |
| `empty_corpus` | boolean | 해당 시 true | 하위호환용. `status=="empty_corpus"`와 동치. |
| `blank_query` | boolean | 해당 시 true | 하위호환용. `status=="blank_query"`와 동치. |
| `reference_only` | boolean | 해당 시 true | 하위호환용. `status=="reference_only"`와 동치. |
| `cluster` | int \| null | ok/reference_only만 int, 나머지 null | 입력 주제가 투영된 KMeans 클러스터 번호(0~5). |
| `query_coord` | `{x:float, y:float}` \| null | ok/reference_only만 객체 | 화면2 지도에 찍을 입력 주제의 SVD 2D 좌표. |
| `count` | int | ok=매칭 건수, 그 외=0 | 임계값 이상 매칭 건수. **공개 필드**(내부 `matched_idx` 아님, §6). |
| `orgs` | string[] | ok=중복제거·정렬 목록, 그 외=`[]` | 매칭 과제 수행 기관 목록. |
| `tasks` | TaskItem[] | §5 | 유사 과제 표(§4.1). |
| `researchers` | ResearcherItem[] | §5 | 연구자 추천 표(§4.2). |
| `researchers_reference_only` | boolean \| null | ok=false, reference_only=true, 나머지 null | 연구자 표가 참고용(임계값 미달)인지. |

---

## 4. 객체 스키마

### 4.1 TaskItem (`tasks[]`)

| 키 | 타입 | 설명 |
|---|---|---|
| `과제명` | string | |
| `주관기관명` | string | |
| `선정년도` | int | |
| `유사도` | float | 소수 3자리 반올림 |
| `클러스터` | int | 0~5 |

### 4.2 ResearcherItem (`researchers[]`)

| 키 | 타입 | 설명 |
|---|---|---|
| `연구책임자명` | string | 동명이인(이름+기관 동일) 11쌍만 뒤에 연구자번호 뒷4자리: `홍길동(1234)` |
| `주관기관명` | string | |
| `특구지역` | string | |
| `대표유사과제명` | string | 해당 연구자의 최고 유사도 과제명 |
| `유사도` | float | 소수 3자리 반올림 |
| `과제수` | int | 임계값 이상 매칭된 과제 수 |

집계 키는 **연구자번호**(이름 아님 — 동명이인 64건 때문). 다운스트림은 이 규칙을 신뢰해도 된다.

---

## 5. 상태별 JSON 예시

**ok**
```json
{
  "status": "ok",
  "empty_corpus": false, "blank_query": false, "reference_only": false,
  "cluster": 3,
  "query_coord": {"x": 0.142, "y": -0.087},
  "count": 30,
  "orgs": ["KAIST", "경북대학교", "전남대학교"],
  "tasks": [
    {"과제명": "…", "주관기관명": "경북대학교", "선정년도": 2021, "유사도": 0.512, "클러스터": 3}
  ],
  "researchers_reference_only": false,
  "researchers": [
    {"연구책임자명": "홍길동", "주관기관명": "경북대학교", "특구지역": "대구", "대표유사과제명": "…", "유사도": 0.512, "과제수": 3}
  ]
}
```

**reference_only** (매칭 0, 참고용)
```json
{
  "status": "reference_only",
  "empty_corpus": false, "blank_query": false, "reference_only": true,
  "cluster": 1,
  "query_coord": {"x": 0.03, "y": 0.21},
  "count": 0,
  "orgs": [],
  "tasks": [ {"과제명": "…", "주관기관명": "…", "선정년도": 2019, "유사도": 0.121, "클러스터": 1} ],
  "researchers_reference_only": true,
  "researchers": [ {"연구책임자명": "…", "주관기관명": "…", "특구지역": "…", "대표유사과제명": "…", "유사도": 0.121, "과제수": 0} ]
}
```

**blank_query**
```json
{
  "status": "blank_query",
  "empty_corpus": false, "blank_query": true, "reference_only": false,
  "cluster": null, "query_coord": null, "count": 0, "orgs": [],
  "tasks": [], "researchers_reference_only": null, "researchers": []
}
```

**empty_corpus**
```json
{
  "status": "empty_corpus",
  "empty_corpus": true, "blank_query": false, "reference_only": false,
  "cluster": null, "query_coord": null, "count": 0, "orgs": [],
  "tasks": [], "researchers_reference_only": null, "researchers": []
}
```

---

## 6. `count` / `matched_idx` 정책

- **`count`는 공개 계약 필드**: 임계값 이상 매칭 건수. 다운스트림이 의존해도 되는 값.
- **`matched_idx`는 내부 전용**: `search_similar_tasks` 내부의 numpy 인덱스 배열(df 행 순서에 결합). HTTP 응답에 노출하지 않으며, 이후 트랙도 여기에 의존하지 않는다. "매칭된 실제 과제 목록"이 필요하면 `tasks`(상위 N) 또는 새 확장 필드로 노출한다.
- `sims`(전체 유사도 배열)도 내부 전용 — `search_similar_tasks` → `main.py`가 `recommend_researchers`에 넘기는 용도로만 쓰고 직렬화 전에 제거한다.

---

## 7. 확장 필드 정책 (A.2/A.3 트랙용)

이후 트랙은 **새 top-level 키만 추가**한다. v1 키의 의미/타입 변경 금지, `status` enum 값 추가 시 이 문서 개정 + 하위호환 유지.

### 7.1 A.2 — 위험도 버킷 (`/api/search`에 추가)

| 키 | 타입 | 상태별 값 | 비고 |
|---|---|---|---|
| `risk_bucket` | `{level, reason}` \| null | ok/reference_only만 객체, blank/empty는 null | 규칙 기반 요약 지표(예측 아님). |
| `risk_bucket.level` | enum string | `높음`/`중간`/`낮음`/`판단 보류` | `reference_only`는 항상 `판단 보류`. |
| `risk_bucket.reason` | string | | 근거 문구(필수 동반). 예: `유사 과제 26건, 최고 유사도 0.416 기준 — 참고용 규칙 판정`. |

버킷 규칙(2×2 → 3단계): `count ≥ RISK_COUNT_HIGH` × `top_sim ≥ RISK_SIM_HIGH`. 둘 다 → 높음 / 하나 → 중간 / 둘 다 아님 → 낮음. **임계값은 실측 캘리브레이션**(`_calibrate_risk.py`, 2026-08-30 재측정) — 예시 3문장 실측 count 37/26/11(하이브리드), 최고유사도 0.728/0.843/0.763(median 0.763) → `RISK_COUNT_HIGH=26`/`RISK_SIM_HIGH=0.76`. 과거 인용 0.22~0.42(임베딩 게이트 도입 전 TF-IDF 단독 값)·211/104/46은 재현 안 됨(폐기). **한계**: 예시가 3개뿐이라 이 값으로도 낮음/중간/높음 3단계가 고르게 안 갈림(현재 예시 기준 높음/높음/낮음) — 실제 배포 시 표본을 늘려 재검토 필요.

### 7.2 A.2 — 중복투자 위험 신호 (선택, `/api/search`에 추가)

| 키 | 타입 | 비고 |
|---|---|---|
| `duplication_risk` | boolean | |
| `risk_count` / `institution_count` / `researcher_count` | int | |
| `duplication_tasks` | TaskItem 유사 객체[] | |

**주의(실데이터 특성)**: 선정년도가 2023~2025 3년 범위뿐 → "선정년도 차이 ≤ 2년" 조건은 항상 참(no-op). 현 데이터에선 "고유사 × 다기관"으로만 판정하고, 연도 조건은 향후 데이터 확장 대비용으로만 문서화.

### 7.3 A.2 — 에고 그래프 / 공백 탐지 (신규 엔드포인트)

`GET /api/ego_graph?query=&top_n=8` — pipeline.py 불변, `main.py`가 `state.df`+`sims`로 조립.

```json
{
  "nodes": [{"id":"q","type":"query|task|researcher|subfield","label":"…","weak":false}],
  "edges": [{"src":"q","dst":"t12","kind":"유사도|수행|소속","w":0.42}],
  "node_count": 34
}
```
노드 캡 30~50. 공백 판정: `type=="subfield"`이고 연결된 매칭 과제 ≤ 2건 → `weak:true`(규칙 기반, 값 발명 없음). 기존 컬럼·유사도만 재사용.

### 7.4 A.3 — 지역 기술편중 (신규 엔드포인트 `GET /api/region`)

`GET /api/region?query=&threshold=0.15` — **별도 경로**. `/api/search`(1,680 한정)의 어떤 필드도 바꾸지 않는다.

**설계 근거(중요):**
- `/api/search`·`/api/clusters`·`/api/ego_graph`는 **특구소속 1,680건** 코퍼스 위에서 동작한다(불변).
- "유사 과제 중 특구소속 비율"은 1,680건만으로는 항상 100%라 무의미하므로, **`/api/region`만 전체 코퍼스(보안 제외 11,783건)에 질의**한다. 이를 위해 `pipeline.PipelineState`에 전체 코퍼스 TF-IDF·임베딩 참조 인덱스를 **추가**했다(검색 파이프라인과 독립).
- 규모지표는 `특구입주기업현황.csv`의 **특구별 입주기업 수**를 쓴다. `특구통계조사총괄.csv`는 `구분`=연도(2005~2024)인 **전국 연도별 합계 시계열**이라 특구별 정규화에 못 쓴다.
- 특구명 정규화: `강소(경기안산)` 등 세분 표기를 `강소`로 통합 → 6개 특구(대덕/대구/광주/부산/전북/강소).

**응답 envelope (모든 상태 공통, 비해당 시 `null`/`0`/`[]`):**

| 키 | 타입 | 상태별 값 | 설명 |
|---|---|---|---|
| `status` | enum string | `ok`/`reference_only`/`blank_query`/`empty_corpus` | 유일 판별자. |
| `empty_corpus`/`blank_query`/`reference_only` | boolean | 하위호환 | `status`와 동치. |
| `total_matched` | int | ok=전체 코퍼스 임계값 이상 매칭 수, 그 외 0 | 특구+비특구 합. |
| `특구소속_matched` | int | ok=그 중 특구소속 수, 그 외 0 | ≤ `total_matched`. |
| `특구소속_비율` | float \| null | ok=`특구소속_matched/total_matched`(0~1), 그 외 null | 매칭 0이면 null. |
| `regions` | RegionItem[] | ok=특구별 분포(과제수 내림차순, 최대 6), 그 외 `[]` | 특구소속 매칭 기준. |
| `top3` | RegionItem[] | `regions[:3]` | 편의 필드. |
| `concentration` | ConcItem[] | **항상 6행**(query 무관 고정) | 전체 1,680건 기준 편중지표(LQ). |
| `scale_note` | string | 항상 | 규모지표 출처 안내(입주기업수, 통계조사총괄 불가). |

**RegionItem**: `{특구:string, count:int, share:float, 입주기업수:int, 집중도_LQ:float|null}` — `share`=count/특구소속_matched.
**ConcItem**: `{특구, 과제수, 과제_비중, 입주기업수, 기업_비중, 집중도_LQ}` — LQ=과제_비중/기업_비중. >1 과집중, <1 과소.

**편중지표(고정, 2026-08-30 실측)**: 대덕 LQ 0.59 · 대구 2.79 · 광주 1.46 · 강소 1.40 · 전북 1.38 · 부산 0.38. → 대구가 기업 기반 대비 과제 과집중, 대덕·부산 과소.

**검증**: `03_webapp/backend/_verify_region.py`(실 파이프라인 임베딩 포함) + 클라우드 TF-IDF 로직 테스트로 join=1680·정규화·LQ 수식·4상태 envelope·`특구소속_matched≤total_matched` 통과.

---

모든 확장 필드는 **모든 상태에서 존재**(비해당 시 `null`/`false`/`0`/`[]`)하도록 추가 — envelope 균일성 원칙 유지.

---

## 8. 안정화 체크리스트 (현재 → 고정)

A.1에서 실제로 고쳐야 하는 항목:

1. `empty_corpus` 응답에 `blank_query` 등 키 누락 → **모든 상태에 3개 boolean(`empty_corpus`/`blank_query`/`reference_only`) + 균일 envelope 항상 포함.**
2. 상태 판별자 부재(boolean 조합 추론) → **`status` enum 필드 추가**(하위호환 위해 기존 boolean 유지).
3. `blank_query`/`empty_corpus`에서 `cluster`/`count`/`orgs` 부재 → **기본값(`null`/`0`/`[]`)으로 항상 포함.**
4. 유사도 소수 3자리 반올림 — 이미 적용됨, 계약으로 명문화.

구현은 `main.py`의 `get_search` 한 곳에서 envelope를 조립하는 방식 권장(§ 아래 패치). `pipeline.py`의 `search_similar_tasks` 반환 형태는 건드리지 않아도 됨 — main에서 정규화하면 리스크 최소.

---

## 9. 버전 관리

- v1: 본 문서. A.1 baseline.
- 변경 시: 버전 올리고 상단 "원칙" 준수. 파괴적 변경은 새 경로(`/api/search/v2`)로 분기.
