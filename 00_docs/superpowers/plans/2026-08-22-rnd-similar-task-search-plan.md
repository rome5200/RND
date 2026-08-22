# R&D 특구 유사 과제 검색 프로토타입 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 준비 중인 과제 주제를 입력하면 R&D 특구 소속 기관이 수행한 유사 과제와, 그 과제를 수행한 연구자
추천 표를 보여주는 Jupyter 노트북 1개(화면1: 검색+추천, 화면2: 클러스터 지도)를 완성한다.

**Architecture:** 단일 Jupyter 노트북(`02_notebook/similar_task_search.ipynb`) 안에서 pandas로 데이터를
적재·조인하고, scikit-learn TF-IDF 벡터화 결과 하나를 코사인 유사도 검색·TruncatedSVD+KMeans 클러스터링·
연구자 집계 세 곳에서 재사용한다. UI는 ipywidgets(화면1), Plotly(화면2)로 노트북 셀 출력에 직접 렌더링한다.
서버/DB/외부 API 없음 — 전부 로컬 프로세스 메모리 내 연산.

**Tech Stack:** Python 3.13.15, `.venv` 가상환경, pandas, scikit-learn, plotly, ipywidgets, notebook/nbconvert

**Spec:** `00_docs/superpowers/specs/2026-08-21-rnd-similar-task-search-design.md` (개정 2, 사용자 승인 완료
2026-08-22) — 이 계획의 모든 결정은 이 스펙을 따른다. 스펙과 이 계획이 충돌하면 스펙이 우선이며, 충돌을
발견하면 구현을 멈추고 사용자에게 확인한다.

## Global Constraints

- 데이터 파일은 `01_data/특구입주기업현황.csv`, `01_data/이알앤디_과제정보.csv` — 인코딩 **cp949** (utf-8로
  열면 깨짐). 두 파일 모두 `.gitignore`에 의해 저장소에 커밋되지 않는다 — **이 규칙을 바꾸지 않는다** (연구자
  실명 + 연구자번호 포함).
- `이알앤디_과제정보`에서 `보안과제여부 == 'Y'`인 5건은 **조인 전에** 제외한다 (11,788건 → 11,783건).
- 기관명 조인은 **양쪽 다 `.str.strip()`만 적용 후 정확 매칭** — 법인 접미사 제거는 하지 않는다. (아래
  "정규화 방식 확정 근거" 참고. 결과는 반드시 **27개 기관 / 1,680건**과 일치해야 하며, 다르면 정규화 로직이
  잘못된 것이다.)
- 연구자 집계는 항상 **`연구자번호` 기준** — 이름으로 groupby 금지 (동명이인 64건, 이름+기관 동일 11쌍).
- 코사인 유사도 임계값 / KMeans k값 / Top-N(유사 과제·연구자 추천)은 Task 9에서 실제 데이터를 보고
  최종 확정한다. 확정 후에는 **발표 당일 라이브로 바꾸지 않는다** (랭킹 드롭다운 전환은 예외 — 의도된
  기능이므로 자유롭게 전환 가능).
- 개인정보 보호: 노트북 출력에는 연구자 실명이 그대로 나타난다(화면 기능상 불가피). 하지만 **커밋 전에는
  반드시 셀 출력을 지운다** (`jupyter nbconvert --clear-output --inplace`) — CSV를 커밋하지 않는 것과 같은
  이유. 이 규칙은 스펙에 명시되어 있지 않지만 기존 정책(HANDOFF.md 8절)의 연장이므로, 다르게 하고 싶으면
  진행 전 사용자에게 확인한다.
- 테스트 코드/CI는 스펙 3장에서 명시적으로 범위 제외(프로토타입 목적, 속도 우선). 이 계획의 "검증"은 pytest가
  아니라 **노트북 셀을 실제로 실행해 값과 assert를 확인**하는 방식이다.

### 정규화 방식 확정 근거 (구현 계획 작성 중 실측)

스펙 5장은 "법인 접미사 제거 등" 정규화를 언급하지만, 실제로 재현 실험한 결과 **접미사 제거를 하면 오히려
27개/1,680건이 아니라 30개/2,008건으로 늘어난다** (매칭된 27개 기관은 전부 대학·출연연·진흥원 이름이라
"주식회사/(주)/재단법인" 같은 접미사가 원래 없고, 접미사 제거 정규화가 다른 무관한 기관명을 우연히 겹치게
만든다). `.str.strip()`만 적용하고 회사 쪽 중복 기관명(96개, 지역/지구만 다르고 이름이 같은 행)을
`drop_duplicates`로 제거한 뒤 조인하면 HANDOFF.md에 기록된 모든 실측치(27기관/1,680건/연구자 1,464명/
1건 1,272명·2건 168명·3건 24명/동명이인 64건/이름+기관 동일 11쌍/상위 기관 순위)가 **정확히** 재현된다.
아래 Task 2의 코드는 이 방식(strip-only)을 사용한다.

---

### Task 1: 개발 환경 준비

**Files:**
- Create: `.venv/` (가상환경, 이미 이 계획 작성 중 생성·검증됨 — 존재하면 재생성하지 않음)
- Create: `requirements.txt`

**Interfaces:**
- Consumes: 없음
- Produces: `.venv\Scripts\python.exe` — 이후 모든 Task가 이 인터프리터를 사용

- [ ] **Step 1: `.venv` 존재 확인, 없으면 생성**

```powershell
if (-not (Test-Path "C:\project\.venv\Scripts\python.exe")) {
    & "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe" -m venv C:\project\.venv
}
```

- [ ] **Step 2: 패키지 설치 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m pip install pandas scikit-learn plotly ipywidgets notebook nbformat --quiet
```

Expected: 에러 없이 종료 (이미 설치돼 있으면 "Requirement already satisfied"만 출력)

- [ ] **Step 3: `requirements.txt` 생성**

```powershell
C:\project\.venv\Scripts\python.exe -m pip freeze | Select-String -Pattern '^(pandas|scikit-learn|scipy|numpy|plotly|ipywidgets|notebook|nbformat|nbconvert|jupyterlab|ipykernel)==' | Out-File -Encoding utf8 C:\project\requirements.txt
```

Expected: `requirements.txt`에 위 패키지들의 고정 버전이 한 줄씩 기록됨

- [ ] **Step 4: 커널 동작 확인**

```powershell
C:\project\.venv\Scripts\python.exe -c "import pandas, sklearn, plotly, ipywidgets; print('OK', pandas.__version__, sklearn.__version__)"
```

Expected: `OK 3.0.5 1.9.0` 형태로 에러 없이 출력

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt for prototype venv"
```

(`.venv/`는 `.gitignore`에 이미 포함되어 커밋되지 않음)

---

### Task 2: 데이터 로드 · 보안과제 제외 · 기관 조인

**Files:**
- Create: `02_notebook/similar_task_search.ipynb` (새 노트북, 이 Task에서 최초 생성)

**Interfaces:**
- Consumes: `01_data/특구입주기업현황.csv`, `01_data/이알앤디_과제정보.csv`
- Produces: `df` (DataFrame, 1,680행) — 컬럼: `사업년도, 선정년도, 대사업명, 중사업명, 소사업명,
  세부사업명, 과제명, 연구책임자명, 연구자번호, 주관기관명, 보안과제여부, 특구지역`. 이후 모든 Task가
  이 `df`를 그대로 사용(추가 필터링 없음).

- [ ] **Step 1: 노트북 생성 및 첫 마크다운 셀 작성**

`NotebookEdit`으로 `02_notebook/similar_task_search.ipynb`를 새로 만들고 첫 셀(마크다운)에 스토리라인
제목을 넣는다:

```markdown
# R&D 특구 유사 과제 검색 프로토타입

준비 중인 연구 주제를 입력하면, R&D 특구 소속 기관이 수행한 유사 과제와 그 과제를 수행한 연구자를
찾아줍니다.
```

- [ ] **Step 2: 데이터 로드 + 보안과제 제외 셀**

```python
import pandas as pd

DATA_DIR = "../01_data"

companies = pd.read_csv(f"{DATA_DIR}/특구입주기업현황.csv", encoding="cp949")
tasks_raw = pd.read_csv(f"{DATA_DIR}/이알앤디_과제정보.csv", encoding="cp949")

print("특구입주기업현황:", len(companies), "건")
print("이알앤디_과제정보 (원본):", len(tasks_raw), "건")

tasks = tasks_raw[tasks_raw["보안과제여부"] != "Y"].copy()
print("보안과제 제외 후:", len(tasks), "건")
assert len(tasks) == 11783, f"보안과제 제외 후 건수가 예상과 다름: {len(tasks)}"
```

Expected 출력: `특구입주기업현황: 6359 건`, `이알앤디_과제정보 (원본): 11788 건`,
`보안과제 제외 후: 11783 건`. assert 통과.

- [ ] **Step 3: 기관명 정규화 + 조인 셀**

```python
companies = companies.rename(columns={"지역": "특구지역"})
companies["_key"] = companies["기관명"].str.strip()
tasks["_key"] = tasks["주관기관명"].str.strip()

companies_dedup = companies.drop_duplicates(subset="_key")

df = (
    tasks.merge(companies_dedup[["_key", "특구지역"]], on="_key", how="inner")
    .drop(columns=["_key"])
    .reset_index(drop=True)
)

print("조인 결과:", len(df), "건 /", df["주관기관명"].nunique(), "개 기관")
assert len(df) == 1680, f"조인 건수가 예상과 다름: {len(df)}"
assert df["주관기관명"].nunique() == 27, f"조인 기관 수가 예상과 다름: {df['주관기관명'].nunique()}"
assert df["연구자번호"].nunique() == 1464, f"연구자 수가 예상과 다름: {df['연구자번호'].nunique()}"
```

Expected 출력: `조인 결과: 1680 건 / 27 개 기관`. 세 assert 모두 통과 (통과하지 않으면 정규화 로직이
잘못된 것 — Global Constraints의 "정규화 방식 확정 근거" 참고).

- [ ] **Step 4: 동명이인 표기가 필요한 (이름, 기관) 쌍 사전 계산**

```python
_name_org_ids = (
    df.drop_duplicates(subset=["연구책임자명", "주관기관명", "연구자번호"])
    .groupby(["연구책임자명", "주관기관명"])["연구자번호"]
    .nunique()
)
DUP_NAME_ORG_PAIRS = set(_name_org_ids[_name_org_ids > 1].index)
print("동명이인 표기 대상 (이름+기관) 쌍:", len(DUP_NAME_ORG_PAIRS))
assert len(DUP_NAME_ORG_PAIRS) == 11, f"동명이인 쌍 수가 예상과 다름: {len(DUP_NAME_ORG_PAIRS)}"

def display_researcher_name(row, dup_pairs=DUP_NAME_ORG_PAIRS):
    key = (row["연구책임자명"], row["주관기관명"])
    if key in dup_pairs:
        return f"{row['연구책임자명']}({str(int(row['연구자번호']))[-4:]})"
    return row["연구책임자명"]
```

Expected 출력: `동명이인 표기 대상 (이름+기관) 쌍: 11`. assert 통과.

- [ ] **Step 5: 노트북 실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료 (assert가 하나라도 실패하면 nbconvert가 non-zero exit code로 실패함)

- [ ] **Step 6: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: load, filter security tasks, join institutions into 1,680-row dataset"
```

(커밋 전 셀 출력에 실명이 포함되지만, 이 시점엔 아직 검색 UI가 없어 노출 범위가 작음 — 그래도 Task 10에서
최종 커밋 전에 반드시 `--clear-output`을 실행한다.)

---

### Task 3: TF-IDF 벡터화 + TruncatedSVD + KMeans 클러스터링

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (새 셀 추가)

**Interfaces:**
- Consumes: `df` (Task 2)
- Produces: `vectorizer` (fitted `TfidfVectorizer`), `tfidf_matrix` (1680 x V), `svd` (fitted
  `TruncatedSVD`), `coords` (1680 x 2 ndarray), `kmeans` (fitted `KMeans`), `clusters` (길이 1680
  ndarray, `df`와 같은 순서) — Task 4/5/7이 모두 이 다섯 개를 그대로 재사용(재적합 금지)

- [ ] **Step 1: 벡터화 + 차원축소 + 클러스터링 셀**

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(df["과제명"])
print("TF-IDF 행렬 크기:", tfidf_matrix.shape)

svd = TruncatedSVD(n_components=2, random_state=42)
coords = svd.fit_transform(tfidf_matrix)

N_CLUSTERS = 6  # Task 9에서 화면2 산점도를 보고 최종 확정

kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
clusters = kmeans.fit_predict(coords)

df["_cluster"] = clusters
print("클러스터별 건수:")
print(df["_cluster"].value_counts().sort_index())
```

Expected: `TF-IDF 행렬 크기: (1680, N)` (N은 8000 전후, 실행마다 동일해야 함 — 코퍼스가 고정이므로).
클러스터별 건수 6개 그룹 모두 0보다 큼(빈 클러스터 없음).

- [ ] **Step 2: 빈 클러스터 없음 assert**

```python
sizes = df["_cluster"].value_counts()
assert len(sizes) == N_CLUSTERS, f"빈 클러스터 존재: {len(sizes)}/{N_CLUSTERS}"
assert (sizes > 0).all()
```

Expected: 통과

- [ ] **Step 3: nbconvert 재실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료

- [ ] **Step 4: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: build shared TF-IDF + SVD + KMeans pipeline"
```

---

### Task 4: 코사인 유사도 검색 함수 (화면1 데이터 레이어)

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (새 셀 추가)

**Interfaces:**
- Consumes: `df`, `vectorizer`, `tfidf_matrix`, `svd`, `kmeans` (Task 2·3)
- Produces: `search_similar_tasks(query, threshold, top_n) -> dict` — 반환 키:
  `empty_corpus: bool`, `blank_query: bool`, `reference_only: bool`, `count: int`, `orgs: list[str]`,
  `table: DataFrame`, `cluster: int`, `sims: np.ndarray (len(df),)`.
  `sims`는 Task 5의 연구자 집계 함수가 재계산 없이 그대로 재사용한다.

- [ ] **Step 1: 검색 함수 셀**

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

SIMILARITY_THRESHOLD = 0.15  # Task 9에서 최종 확정
TOP_N_TASKS = 5              # Task 9에서 최종 확정

def search_similar_tasks(query, threshold=SIMILARITY_THRESHOLD, top_n=TOP_N_TASKS):
    if len(df) == 0:
        return {"empty_corpus": True}

    if query is None or not query.strip():
        return {"empty_corpus": False, "blank_query": True}

    query_vec = vectorizer.transform([query])
    sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
    query_coord = svd.transform(query_vec)
    query_cluster = int(kmeans.predict(query_coord)[0])

    mask = sims >= threshold
    matched_idx = np.where(mask)[0]

    if len(matched_idx) == 0:
        fallback_idx = np.argsort(-sims)[:3]
        table = df.iloc[fallback_idx][["과제명", "주관기관명", "선정년도"]].copy()
        table["유사도"] = sims[fallback_idx]
        table["클러스터"] = df.iloc[fallback_idx]["_cluster"].values
        return {
            "empty_corpus": False, "blank_query": False, "reference_only": True,
            "count": 0, "orgs": [], "table": table, "cluster": query_cluster, "sims": sims,
        }

    ordered = matched_idx[np.argsort(-sims[matched_idx])][:top_n]
    table = df.iloc[ordered][["과제명", "주관기관명", "선정년도"]].copy()
    table["유사도"] = sims[ordered]
    table["클러스터"] = df.iloc[ordered]["_cluster"].values
    return {
        "empty_corpus": False, "blank_query": False, "reference_only": False,
        "count": len(matched_idx),
        "orgs": sorted(df.iloc[matched_idx]["주관기관명"].unique().tolist()),
        "table": table, "cluster": query_cluster, "sims": sims,
    }
```

- [ ] **Step 2: 예시 3문장 + 엣지 케이스로 직접 호출해 확인**

```python
for q in ["인공지능 기반 이미지 분석 기술 개발", "이차전지 소재 개발 연구", "탄소중립 에너지 저장 시스템 개발"]:
    r = search_similar_tasks(q)
    print(q, "-> count:", r["count"], "reference_only:", r["reference_only"], "cluster:", r["cluster"])
    assert r["count"] > 0 or r["reference_only"], f"'{q}'에 대해 표시할 행이 없음"

for q in ["", "   ", "가", "a"]:
    r = search_similar_tasks(q)
    print(repr(q), "-> blank:", r.get("blank_query"), "reference_only:", r.get("reference_only"))
```

Expected: 예시 3문장 모두 `count > 0` (임계값 0.15에서 최소 1건 이상 매칭됨 — 실측: "인공지능..." 약
30건, "이차전지..." 약 8건, "탄소중립..." 약 4건 매칭). 빈 문자열/공백은 `blank_query: True`. `"가"`,
`"a"`는 에러 없이 `reference_only: True`로 처리됨(전부 유사도 0). 파이썬 예외(트레이스백) 발생 안 함.

- [ ] **Step 3: nbconvert 재실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료

- [ ] **Step 4: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: add cosine-similarity search with 0-result fallback"
```

---

### Task 5: 연구자 추천 집계 함수

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (새 셀 추가)

**Interfaces:**
- Consumes: `df`, `sims` (Task 4의 `search_similar_tasks` 반환값 안의 `sims`), `display_researcher_name`
  (Task 2)
- Produces: `recommend_researchers(sims, threshold, rank_by, top_n) -> dict` — 반환 키:
  `reference_only: bool`, `table: DataFrame` (표시 컬럼:
  `연구책임자명, 주관기관명, 특구지역, 대표 유사 과제명, 유사도, 과제수`)

- [ ] **Step 1: 집계 함수 셀**

```python
TOP_N_RESEARCHERS = 5  # Task 9에서 최종 확정
RANK_OPTIONS = ["최고 유사도", "유사 과제 건수", "합산 점수"]

def recommend_researchers(sims, threshold=SIMILARITY_THRESHOLD, rank_by="최고 유사도", top_n=TOP_N_RESEARCHERS):
    work = df.copy()
    work["유사도"] = sims
    work["임계값이상"] = work["유사도"] >= threshold

    counts_above = work.groupby("연구자번호")["임계값이상"].sum()
    idxmax_all = work.groupby("연구자번호")["유사도"].idxmax()
    rep = work.loc[
        idxmax_all,
        ["연구자번호", "연구책임자명", "주관기관명", "특구지역", "과제명", "유사도"],
    ].rename(columns={"과제명": "대표 유사 과제명"}).set_index("연구자번호")
    sum_above = work[work["임계값이상"]].groupby("연구자번호")["유사도"].sum()

    researchers = rep.copy()
    researchers["과제수"] = counts_above.reindex(researchers.index).fillna(0).astype(int)
    researchers["합산점수"] = sum_above.reindex(researchers.index).fillna(0.0)
    researchers = researchers.reset_index()

    qualifying = researchers[researchers["과제수"] > 0]

    if len(qualifying) == 0:
        selected = researchers.sort_values("유사도", ascending=False).head(3)
        reference_only = True
    else:
        if rank_by == "유사 과제 건수":
            selected = qualifying.sort_values(["과제수", "유사도"], ascending=[False, False])
        elif rank_by == "합산 점수":
            selected = qualifying.sort_values("합산점수", ascending=False)
        else:
            selected = qualifying.sort_values("유사도", ascending=False)
        selected = selected.head(top_n)
        reference_only = False

    selected = selected.copy()
    selected["연구책임자명"] = selected.apply(display_researcher_name, axis=1)
    display_cols = ["연구책임자명", "주관기관명", "특구지역", "대표 유사 과제명", "유사도", "과제수"]
    return {"reference_only": reference_only, "table": selected[display_cols]}
```

- [ ] **Step 2: 예시 3문장 × 랭킹 3종 = 9회 호출로 확인 (완료조건 4 사전 점검)**

```python
example_queries = ["인공지능 기반 이미지 분석 기술 개발", "이차전지 소재 개발 연구", "탄소중립 에너지 저장 시스템 개발"]

for q in example_queries:
    r_search = search_similar_tasks(q)
    for rank_by in RANK_OPTIONS:
        r_rec = recommend_researchers(r_search["sims"], rank_by=rank_by)
        n_rows = len(r_rec["table"])
        print(q, "|", rank_by, "-> rows:", n_rows, "reference_only:", r_rec["reference_only"])
        assert n_rows >= 1, f"'{q}' / '{rank_by}' 조합에서 연구자 추천 행이 0개"
```

Expected: 9줄 모두 `rows >= 1` 이고 에러 없이 출력됨.

- [ ] **Step 3: 동명이인 표기가 실제로 발생하는지 확인**

```python
labeled = [r for _, r in researchers.iterrows() if "(" in display_researcher_name(r)]
print("괄호 표기가 붙은 연구자 수 (전체 1,464명 중):", len(labeled))
assert len(labeled) > 0, "동명이인 표기 로직이 한 번도 발생하지 않음 — 로직 점검 필요"
```

Expected: `0`보다 큰 수 출력 (11쌍 중 최소 일부는 실제로 표기됨)

- [ ] **Step 4: nbconvert 재실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료

- [ ] **Step 5: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: add researcher recommendation aggregation by 연구자번호"
```

---

### Task 6: 화면 1 — ipywidgets UI 결합

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (새 셀 추가)

**Interfaces:**
- Consumes: `search_similar_tasks`, `recommend_researchers`, `RANK_OPTIONS` (Task 4·5)
- Produces: `text_input`, `rank_dropdown`, `search_button`, `output_area` (ipywidgets 인스턴스),
  `on_search_clicked(_)` (버튼 콜백 — 위젯 없이도 직접 호출해 테스트 가능하도록 이름 있는 함수로 정의)

- [ ] **Step 1: 위젯 + 콜백 정의 셀**

```python
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

text_input = widgets.Text(description="과제 주제:", placeholder="준비 중인 과제의 주제를 입력하세요", layout=widgets.Layout(width="500px"))
rank_dropdown = widgets.Dropdown(options=RANK_OPTIONS, value="최고 유사도", description="랭킹 기준:")
search_button = widgets.Button(description="검색", button_style="primary")
output_area = widgets.Output()

def render_results(query, rank_by):
    with output_area:
        clear_output()
        result = search_similar_tasks(query)

        if result.get("empty_corpus"):
            print("특구 소속 기관이 수행한 과제 데이터가 없습니다.")
            return
        if result.get("blank_query"):
            print("검색어를 입력해주세요.")
            return

        print(f"내 주제가 속한 것으로 추정되는 클러스터 번호: {result['cluster']}")

        if result["reference_only"]:
            print("정확히 일치하는 유사 과제를 찾지 못했습니다. 아래는 유사도가 가장 높았던 3건입니다(참고용).")
        else:
            print(f"유사 과제 건수: {result['count']}건")
            print("수행 기관:", ", ".join(result["orgs"]))
        display(result["table"])

        rec = recommend_researchers(result["sims"], rank_by=rank_by)
        if rec["reference_only"]:
            print("참고용 — 임계값 미달: 유사도가 가장 높은 연구자 3명입니다.")
        print("연구자 추천")
        display(rec["table"])

def on_search_clicked(_):
    render_results(text_input.value, rank_dropdown.value)

def on_rank_changed(_):
    render_results(text_input.value, rank_dropdown.value)

search_button.on_click(on_search_clicked)
rank_dropdown.observe(on_rank_changed, names="value")

display(widgets.HBox([text_input, rank_dropdown, search_button]))
display(output_area)
```

- [ ] **Step 2: 콜백을 직접 호출해 위젯 없이도 동작 확인 (완료조건 1·3·4의 함수 레벨 사전 검증)**

```python
for q in ["인공지능 기반 이미지 분석 기술 개발", "이차전지 소재 개발 연구", "탄소중립 에너지 저장 시스템 개발", "", "가"]:
    text_input.value = q
    for rank_by in RANK_OPTIONS:
        rank_dropdown.value = rank_by
        on_search_clicked(None)  # output_area에 렌더링, 예외 발생 시 여기서 즉시 실패
print("모든 조합 실행 완료 — 예외 없음")
```

Expected: `모든 조합 실행 완료 — 예외 없음` 출력, 위 셀 실행 중 트레이스백이 하나도 뜨지 않음.

- [ ] **Step 3: nbconvert 재실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료. (주의: `nbconvert --execute`는 실제 버튼 클릭 이벤트를 발생시키지 않으므로, 이
Step은 위 Step 2에서 이미 명시적으로 `on_search_clicked(None)`을 호출해 두었기 때문에 통과한다. 위젯이
브라우저에서 실제로 클릭 가능한지는 Task 10에서 사용자가 직접 Jupyter를 열어 확인한다.)

- [ ] **Step 4: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: wire up screen 1 ipywidgets UI (text input + rank dropdown + button)"
```

---

### Task 7: 화면 2 — Plotly 클러스터 지도

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (새 셀 추가)

**Interfaces:**
- Consumes: `df`, `coords`, `clusters`, `search_similar_tasks` (Task 3·4)
- Produces: `render_cluster_map(query)` — 호출 시 Plotly Figure를 표시하고, 화면1과 동일한 `cluster`
  번호로 하이라이트 마커를 그린다 (동일한 `kmeans.predict` 호출을 재사용하므로 번호 불일치가 구조적으로
  발생할 수 없음)

- [ ] **Step 1: 산점도 함수 셀**

```python
import plotly.graph_objects as go

def render_cluster_map(query):
    fig = go.Figure()
    for c in sorted(df["_cluster"].unique()):
        sub = df[df["_cluster"] == c]
        fig.add_trace(go.Scatter(
            x=coords[sub.index, 0], y=coords[sub.index, 1],
            mode="markers", name=f"클러스터 {c}",
            marker=dict(size=6),
            hovertext=[
                f"{row['과제명']}<br>{row['주관기관명']}<br>{row['특구지역']}<br>클러스터 {c}"
                for _, row in sub.iterrows()
            ],
            hoverinfo="text",
        ))

    result = search_similar_tasks(query)
    if not result.get("blank_query") and not result.get("empty_corpus"):
        query_vec = vectorizer.transform([query])
        qx, qy = svd.transform(query_vec)[0]
        fig.add_trace(go.Scatter(
            x=[qx], y=[qy], mode="markers+text",
            marker=dict(size=16, symbol="star", color="black"),
            text=[f"내 주제 (클러스터 {result['cluster']})"], textposition="top center",
            name="내 주제",
        ))
        assert result["cluster"] in df["_cluster"].unique(), "화면1 클러스터 번호가 화면2 클러스터 목록에 없음"

    fig.update_layout(title="전체 과제 클러스터 지도", xaxis_title="SVD 1", yaxis_title="SVD 2")
    fig.show()
    return fig

render_cluster_map("이차전지 소재 개발 연구")
```

Expected: Figure가 렌더링되고(노트북 실행 환경에서는 HTML 출력), assert가 통과함. `nbconvert --execute`
환경에서는 Plotly가 정적 이미지 대신 JS 위젯 출력을 셀 출력에 남긴다 — 에러 없이 셀이 완료되면 충분하다.

- [ ] **Step 2: 완료조건 2 사전 점검 — 화면1 결과 행의 클러스터 번호가 화면2에 실제로 존재하는지 코드로 대조**

```python
for q in ["인공지능 기반 이미지 분석 기술 개발", "이차전지 소재 개발 연구", "탄소중립 에너지 저장 시스템 개발"]:
    r = search_similar_tasks(q)
    row_clusters = set(r["table"]["클러스터"]) if not r["reference_only"] else set(r["table"]["클러스터"])
    all_clusters = set(df["_cluster"].unique())
    assert row_clusters.issubset(all_clusters), f"'{q}' 결과의 클러스터 번호가 화면2 목록에 없음: {row_clusters - all_clusters}"
print("화면1/화면2 클러스터 번호 대조 완료 — 불일치 없음")
```

Expected: `화면1/화면2 클러스터 번호 대조 완료 — 불일치 없음` 출력

- [ ] **Step 3: nbconvert 재실행 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료

- [ ] **Step 4: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "feat: add screen 2 cluster map with query highlight"
```

---

### Task 8: 발표 스토리라인 마크다운 셀 정리

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (기존 코드 셀 사이에 마크다운 셀 추가, 코드는 변경하지
  않음)

**Interfaces:**
- Consumes: 없음 (문서화 작업)
- Produces: 없음

- [ ] **Step 1: 각 Task가 만든 코드 블록 앞에 마크다운 섹션 헤더 추가**

`NotebookEdit`으로 아래 5개 마크다운 셀을 각 해당 코드 셀 바로 앞에 삽입한다 (정확한 위치는 실제 셀 순서에
맞춰 조정):

```markdown
## 1. 데이터 적재 — 특구 소속 기관이 수행한 과제만 추출
```
```markdown
## 2. 과제명 벡터화 — 검색·클러스터링·연구자 추천이 공유하는 파이프라인
```
```markdown
## 3. 화면 1 — 유사 과제 검색 + 연구자 추천
```
```markdown
## 4. 화면 2 — 전체 과제 클러스터 지도
```
```markdown
## 5. 알려진 한계

TF-IDF 표면 단어 매칭 방식이라, 같은 의미라도 다른 표현("인공지능" vs "AI")을 쓰면 유사 과제로 잡히지
않을 수 있습니다. 반대로 짧은 과제명에서 흔한 단어 하나만 겹쳐도 유사도가 실제보다 높게 나올 수 있습니다.
```

- [ ] **Step 2: nbconvert 재실행 확인 (마크다운만 추가했으므로 결과값은 그대로여야 함)**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료, 이전 assert들 모두 그대로 통과

- [ ] **Step 3: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "docs: add presentation storyline markdown sections to notebook"
```

---

### Task 9: 파라미터 최종 확정 (임계값 / k / Top-N)

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (Task 3의 `N_CLUSTERS`, Task 4의
  `SIMILARITY_THRESHOLD`/`TOP_N_TASKS`, Task 5의 `TOP_N_RESEARCHERS` 셀 값만 수정)

**Interfaces:**
- Consumes: 위 네 변수
- Produces: 위 네 변수의 최종 확정값 (이후 발표 당일까지 변경하지 않음)

- [ ] **Step 1: 발표에 쓸 예시 주제 3개를 최종 확정하고 노트북에 주석으로 고정**

기본 후보(이 계획 작성 중 실측 확인됨 — 임계값 0.15에서 모두 1건 이상 매칭):
`"인공지능 기반 이미지 분석 기술 개발"`, `"이차전지 소재 개발 연구"`, `"탄소중립 에너지 저장 시스템 개발"`.
발표자가 실제로 다룰 주제와 더 가까운 문장이 있다면 이 3개를 교체해도 되지만, 교체 시 이 Step 전체를
그 문장으로 다시 실행해 최소 1건 이상 매칭되는지 반드시 재확인한다.

- [ ] **Step 2: 임계값별 결과 건수 분포를 실제로 출력해 `SIMILARITY_THRESHOLD` 확정**

```python
for t in [0.10, 0.15, 0.20, 0.25]:
    print(f"--- threshold={t} ---")
    for q in ["인공지능 기반 이미지 분석 기술 개발", "이차전지 소재 개발 연구", "탄소중립 에너지 저장 시스템 개발"]:
        r = search_similar_tasks(q, threshold=t)
        print(" ", q, "-> count:", r["count"], "reference_only:", r["reference_only"])
```

이 출력을 보고 세 예시 문장 모두 `reference_only=False`(즉 count > 0)가 되는 가장 엄격한(가장 높은)
임계값을 선택해 Task 4 셀의 `SIMILARITY_THRESHOLD` 값을 갱신한다. (이 계획 작성 중 실측으로는 0.15가
세 문장 모두 count>0을 만족하는 값이었다 — 최종 실행 환경에서 재확인 후 그대로 두거나 조정한다.)

- [ ] **Step 3: `N_CLUSTERS` 확정 — 산점도를 눈으로 보고 판단**

```python
render_cluster_map("이차전지 소재 개발 연구")
```

클러스터 색상이 지나치게 한쪽에 몰리거나(하나의 클러스터가 90% 이상 차지) 지나치게 쪼개지지 않는지
확인한다. 문제가 있으면 Task 3 셀의 `N_CLUSTERS` 값을 4~10 사이에서 조정하고 Task 3 이후 모든 셀을
다시 실행한다.

- [ ] **Step 4: `TOP_N_TASKS`, `TOP_N_RESEARCHERS` 확정**

발표 화면에 표가 너무 길어 스크롤이 생기지 않는 값(5 전후)을 그대로 사용하거나, 예시 3문장의 실제 매칭
건수(Step 2 출력)를 보고 표가 항상 꽉 차 보이도록 조정한다.

- [ ] **Step 5: 확정 후 전체 재실행으로 일관성 확인**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료, 모든 assert 통과

- [ ] **Step 6: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "chore: finalize threshold, k, and Top-N parameters based on observed data"
```

---

### Task 10: 완료조건 4개 최종 검증 + Restart & Run All + 출력 정리 커밋

**Files:**
- Modify: `02_notebook/similar_task_search.ipynb` (실행만, 코드 변경 없음)

**Interfaces:**
- Consumes: 완성된 노트북 전체
- Produces: 없음 (검증 및 최종 커밋)

- [ ] **Step 1: PROJECT_PLAN.md 3절의 완료조건 4개를 하나씩 실제로 확인**

Jupyter를 열어(`C:\project\.venv\Scripts\jupyter.exe notebook 02_notebook/similar_task_search.ipynb`)
"Restart Kernel and Run All"을 실행한 뒤, 브라우저에서 직접:

1. 예시 주제 3개를 입력창에 입력 → 결과 표 행 수가 0이 아님을 확인
2. 결과 표 한 행의 클러스터 번호를 화면2에서 같은 색 점으로 실제로 찾아 대조
3. 입력창을 비우거나 한 글자만 넣고 검색 → 빨간 트레이스백이 뜨지 않음을 확인
4. 예시 3개 × 랭킹 드롭다운 3개 = 9회 전환 → 매번 에러 없이 결과가 바뀌는지 확인

Expected: 4개 모두 통과. 하나라도 실패하면 해당 Task로 돌아가 원인을 고친다.

- [ ] **Step 2: 커밋 전 셀 출력 정리 (PII 노출 최소화)**

```powershell
C:\project\.venv\Scripts\python.exe -m jupyter nbconvert --clear-output --inplace C:\project\02_notebook\similar_task_search.ipynb
```

Expected: 에러 없이 종료. `git diff --stat`으로 노트북 파일 크기가 줄었는지(출력이 실제로 지워졌는지)
확인한다.

- [ ] **Step 3: Commit**

```bash
git add 02_notebook/similar_task_search.ipynb
git commit -m "chore: verify 4 completion criteria, clear notebook outputs before commit"
```

- [ ] **Step 4: 사용자에게 보고**

HANDOFF.md를 갱신해 "구현 완료, 완료조건 4개 확인됨"으로 표시하고, `git push`는 인증 창이 필요해
에이전트가 대신 할 수 없으므로 사용자에게 직접 실행을 요청한다.

---

## Self-Review 체크리스트 (계획 작성자가 직접 확인함)

- **스펙 커버리지**: 3장 범위(포함 항목) 전부 → Task 2~8에 매핑됨. 6.1절 연구자 추천 → Task 5.
  6.1절 0건 처리(이번 세션에 확정한 "연구자 상위 3명 고정") → Task 5 Step 1 코드에 반영됨. 7장 파라미터
  → Task 9. 8장 성공 기준 4개 항목(연구자 추천 2개 포함) → Task 10.
- **플레이스홀더 스캔**: "TODO"/"나중에"/"적절히 처리" 패턴 없음. 모든 코드 블록은 실제 실행 가능한 코드.
- **타입/시그니처 일관성**: `search_similar_tasks`가 반환하는 `sims`를 `recommend_researchers`가 그대로
  받아쓰는 시그니처가 Task 4·5·6·7에서 동일하게 유지됨. `display_researcher_name(row, dup_pairs=...)`가
  Task 2에서 정의되고 Task 5에서 `.apply(display_researcher_name, axis=1)`로 기본값 그대로 호출됨(일치).
