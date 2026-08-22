# R&D 특구 유사 과제 검색 — 2단계 웹앱(FastAPI + 정적 프론트) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 1단계 노트북(`02_notebook/similar_task_search.ipynb`)에서 이미 검증된 검색·클러스터링·연구자
추천 로직을 FastAPI 백엔드로 옮기고, 사용자가 Claude Design으로 만든 목업(`00_docs/design-brief.md` 기반)
을 실제 동작하는 HTML/CSS/JS 프론트엔드로 재현해 2단계 웹앱을 완성한다.

**Architecture:** `03_webapp/backend/pipeline.py`가 데이터 로드·필터·조인·TF-IDF·SVD·KMeans·검색·연구자
집계를 전담하는 순수 함수 모듈(1단계 노트북과 동일한 검증된 알고리즘의 독립 구현 — 노트북 파일 자체는
건드리지 않는다). `03_webapp/backend/main.py`가 FastAPI로 이를 감싸 `/api/clusters`, `/api/search` 두
엔드포인트를 제공한다. `03_webapp/frontend/`는 정적 HTML/CSS/JS로, 목업의 시각 디자인(색상·폰트·레이아웃)
을 그대로 재현하되 목업의 `x-dc`/`sc-for` 같은 Claude Design 전용 태그는 쓰지 않고 순수 fetch() + DOM
렌더링으로 바꾼다. FastAPI가 `StaticFiles`로 프론트를 함께 서빙해 서버 하나(`uvicorn`)로 전체가 뜬다.

**Tech Stack:** Python 3.13.15 (`.venv` 재사용), FastAPI, uvicorn, pandas, scikit-learn (이미 설치됨) +
바닐라 HTML/CSS/JS (프레임워크 없음, 빌드 단계 없음)

**Spec:** `00_docs/superpowers/specs/2026-08-21-rnd-similar-task-search-design.md` (개정 2, 사용자 승인
완료) — 화면 구성·용어·완료조건의 binding authority. 추가로 `00_docs/design-brief.md`(디자인 브리프)와
사용자가 Claude Design에서 받은 목업(`RnD 유사과제 검색.dc.html`, 이 계획 작성 시점에 검토 완료)이 이번
2단계의 시각 디자인 기준이다. 2단계로 범위를 넘기는 것과 FastAPI 채택은 2026-08-22 사용자 승인 완료.

## Global Constraints

- **알고리즘은 1단계와 완전히 동일해야 한다** — 보안과제 제외(`보안과제여부=='Y'` 5건 제거) → 기관명
  양쪽 `.str.strip()` + 정확 매칭(회사측 중복 기관명은 `drop_duplicates` 후 조인, 27개 기관/1,680건 재현
  필수) → TF-IDF(`TfidfVectorizer()` 기본값) → `TruncatedSVD(n_components=2, random_state=42)` →
  `KMeans(n_clusters=6, random_state=42, n_init=10)`(2D `coords`에 적합) → 코사인 유사도(`threshold=0.15`)
  → 연구자 집계(`연구자번호` 기준, 유사도=대표과제 최고유사도 항상, 과제수=임계값 이상 건수,
  0건 시 연구자 상위 3명 고정). 이 값들이 1단계와 다르게 나오면 버그다.
- **노트북 파일(`02_notebook/similar_task_search.ipynb`)은 이 계획에서 수정하지 않는다** — 이미 완료·
  리뷰된 별도 산출물이다. 백엔드 모듈은 독립적인 새 구현이다.
- 데이터 파일 경로/인코딩: `01_data/특구입주기업현황.csv`, `01_data/이알앤디_과제정보.csv`, cp949.
  이 CSV들은 `.gitignore`로 계속 제외된다 — 웹앱도 서버 시작 시 로컬 파일을 읽어 메모리에 올릴 뿐,
  DB나 외부 저장소를 두지 않는다(스펙 3장 "서버/DB 구축 제외" 원칙 유지 — FastAPI는 이 프로토타입의
  "가벼운 로직 서버"이며 상태를 영속 저장하지 않는 인메모리 서버다).
- **클러스터에는 의미 라벨(예: "바이오 소재")을 붙이지 않는다** — 목업은 시연용으로 지어낸 라벨을
  보여주지만, 실제 KMeans 클러스터는 비지도 학습 결과라 "이 클러스터가 실제로 무슨 분야인지"를
  근거 없이 주장하면 스펙 3장에서 기각한 "기술이전 예측"과 같은 문제(없는 값을 발명)가 된다. 프론트
  범례는 노트북과 동일하게 "클러스터 0" ~ "클러스터 5"로만 표시한다.
- 개인정보: API 응답에 `연구자번호`를 원본 그대로 절대 포함하지 않는다. 표시명은 노트북과 동일하게
  이름+기관 겹치는 11쌍만 `홍길동(1234)` 형태.
- 위젯/버튼 등 시각 요소는 목업의 색상(`--mint:#00C08B` 계열)·폰트(NanumSquare, `frontend/fonts/`에
  복사됨)·레이아웃(그리드 컬럼 너비 등)을 최대한 그대로 따른다. 목업의 `_ds/` 디자인시스템 번들
  전체나 `x-dc`/`sc-for`/`sc-if`/`x-import` 커스텀 태그는 가져오지 않는다 — 순수 HTML/CSS/바닐라 JS로
  같은 결과물을 만든다.
- 테스트: 여전히 pytest/CI 없음(스펙 3장 원칙 유지). 검증은 실제로 서버를 띄우고 `curl`/`requests`로
  엔드포인트를 호출해 값을 확인하는 방식.
- 완료조건은 PROJECT_PLAN.md 3절과 동일한 4개를 웹앱에서도 만족해야 한다(예시 3문장 → 결과 1건 이상,
  화면1↔2 클러스터 번호 일치, 빈 입력 시 에러 화면 없음, 연구자 추천 9회 조합 에러 없음).

---

### Task 1: 백엔드 파이프라인 모듈 + FastAPI 스켈레톤

**Files:**
- Create: `03_webapp/backend/pipeline.py`
- Create: `03_webapp/backend/main.py`
- Create: `03_webapp/backend/__init__.py` (빈 파일, 패키지 인식용)
- Modify: `requirements.txt` (fastapi, uvicorn 추가)

**Interfaces:**
- Produces: `pipeline.load_and_build()` → `PipelineState` (dataclass 또는 dict: `df`, `vectorizer`,
  `tfidf_matrix`, `svd`, `coords`, `kmeans`, `dup_pairs`). `pipeline.search_similar_tasks(state, query,
  threshold, top_n)`, `pipeline.recommend_researchers(state, sims, threshold, rank_by, top_n)` — 반환값은
  JSON 직렬화 가능한 dict/list(DataFrame이 아니라 `to_dict("records")` 등으로 변환된 순수 파이썬 값).
  `pipeline.get_cluster_points(state)` → 1,680개 포인트의 `{x, y, cluster, 과제명, 주관기관명, 특구지역}`
  리스트.

- [ ] **Step 1: `requirements.txt`에 웹 서버 의존성 추가**

```powershell
C:\project\.venv\Scripts\python.exe -m pip install fastapi uvicorn --quiet
C:\project\.venv\Scripts\python.exe -m pip freeze | Select-String -Pattern '^(fastapi|uvicorn|starlette|pydantic|anyio|click|h11)==' | ForEach-Object { $_.Line } | Add-Content -Encoding utf8NoBOM C:\project\requirements.txt
```

Expected: `requirements.txt`에 fastapi/uvicorn 및 의존 패키지 버전이 추가됨(BOM 없이, 기존 줄 유지).

- [ ] **Step 2: `pipeline.py` 작성**

```python
"""웹앱 백엔드용 검색·클러스터링·연구자 추천 파이프라인.
02_notebook/similar_task_search.ipynb의 검증된 알고리즘을 API 서버용으로 독립 재구현한 것 — 노트북 파일
자체는 참조/수정하지 않는다."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parents[2] / "01_data"
SIMILARITY_THRESHOLD = 0.15
N_CLUSTERS = 6
TOP_N_TASKS = 5
TOP_N_RESEARCHERS = 5
RANK_OPTIONS = ["최고 유사도", "유사 과제 건수", "합산 점수"]


@dataclass
class PipelineState:
    df: pd.DataFrame
    vectorizer: TfidfVectorizer
    tfidf_matrix: object
    svd: TruncatedSVD
    coords: np.ndarray
    kmeans: KMeans
    dup_pairs: set


def _load_joined_df() -> pd.DataFrame:
    companies = pd.read_csv(DATA_DIR / "특구입주기업현황.csv", encoding="cp949")
    tasks_raw = pd.read_csv(DATA_DIR / "이알앤디_과제정보.csv", encoding="cp949")

    tasks = tasks_raw[tasks_raw["보안과제여부"] != "Y"].copy()
    assert len(tasks) == 11783, f"보안과제 제외 후 건수가 예상과 다름: {len(tasks)}"

    companies = companies.rename(columns={"지역": "특구지역"})
    companies["_key"] = companies["기관명"].str.strip()
    tasks["_key"] = tasks["주관기관명"].str.strip()
    companies_dedup = companies.drop_duplicates(subset="_key")

    df = (
        tasks.merge(companies_dedup[["_key", "특구지역"]], on="_key", how="inner")
        .drop(columns=["_key"])
        .reset_index(drop=True)
    )
    assert len(df) == 1680, f"조인 건수가 예상과 다름: {len(df)}"
    assert df["주관기관명"].nunique() == 27, f"조인 기관 수가 예상과 다름: {df['주관기관명'].nunique()}"
    assert df["연구자번호"].nunique() == 1464, f"연구자 수가 예상과 다름: {df['연구자번호'].nunique()}"
    return df


def _compute_dup_pairs(df: pd.DataFrame) -> set:
    ids = (
        df.drop_duplicates(subset=["연구책임자명", "주관기관명", "연구자번호"])
        .groupby(["연구책임자명", "주관기관명"])["연구자번호"]
        .nunique()
    )
    pairs = set(ids[ids > 1].index)
    assert len(pairs) == 11, f"동명이인 쌍 수가 예상과 다름: {len(pairs)}"
    return pairs


def display_researcher_name(row, dup_pairs: set) -> str:
    key = (row["연구책임자명"], row["주관기관명"])
    if key in dup_pairs:
        return f"{row['연구책임자명']}({str(int(row['연구자번호']))[-4:]})"
    return row["연구책임자명"]


def load_and_build() -> PipelineState:
    df = _load_joined_df()
    dup_pairs = _compute_dup_pairs(df)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(df["과제명"])

    svd = TruncatedSVD(n_components=2, random_state=42)
    coords = svd.fit_transform(tfidf_matrix)

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(coords)
    df["_cluster"] = clusters

    sizes = df["_cluster"].value_counts()
    assert len(sizes) == N_CLUSTERS and (sizes > 0).all(), "빈 클러스터 존재"

    return PipelineState(
        df=df, vectorizer=vectorizer, tfidf_matrix=tfidf_matrix,
        svd=svd, coords=coords, kmeans=kmeans, dup_pairs=dup_pairs,
    )


def get_cluster_points(state: PipelineState) -> list[dict]:
    df = state.df
    return [
        {
            "x": float(state.coords[i, 0]), "y": float(state.coords[i, 1]),
            "cluster": int(df.iloc[i]["_cluster"]),
            "과제명": df.iloc[i]["과제명"], "주관기관명": df.iloc[i]["주관기관명"],
            "특구지역": df.iloc[i]["특구지역"],
        }
        for i in range(len(df))
    ]


def search_similar_tasks(state: PipelineState, query: str, threshold: float = SIMILARITY_THRESHOLD,
                          top_n: int = TOP_N_TASKS) -> dict:
    df = state.df
    if len(df) == 0:
        return {"empty_corpus": True}
    if query is None or not query.strip():
        return {"empty_corpus": False, "blank_query": True}

    query_vec = state.vectorizer.transform([query])
    sims = cosine_similarity(query_vec, state.tfidf_matrix).flatten()
    query_coord = state.svd.transform(query_vec)[0]
    query_cluster = int(state.kmeans.predict(state.svd.transform(query_vec))[0])

    mask = sims >= threshold
    matched_idx = np.where(mask)[0]

    def _row_to_dict(i, sim):
        return {
            "과제명": df.iloc[i]["과제명"], "주관기관명": df.iloc[i]["주관기관명"],
            "선정년도": int(df.iloc[i]["선정년도"]), "유사도": round(float(sim), 3),
            "클러스터": int(df.iloc[i]["_cluster"]),
        }

    base = {
        "empty_corpus": False, "blank_query": False,
        "cluster": query_cluster,
        "query_coord": {"x": float(query_coord[0]), "y": float(query_coord[1])},
        "sims": sims,  # 호출자(main.py)가 recommend_researchers에 그대로 넘김 — 응답 직렬화 전에 제거해야 함
    }

    if len(matched_idx) == 0:
        fallback_idx = np.argsort(-sims)[:3]
        base.update(reference_only=True, count=0, orgs=[],
                     table=[_row_to_dict(i, sims[i]) for i in fallback_idx])
        return base

    ordered = matched_idx[np.argsort(-sims[matched_idx])][:top_n]
    base.update(
        reference_only=False, count=int(len(matched_idx)),
        orgs=sorted(df.iloc[matched_idx]["주관기관명"].unique().tolist()),
        table=[_row_to_dict(i, sims[i]) for i in ordered],
    )
    return base


def recommend_researchers(state: PipelineState, sims: np.ndarray, threshold: float = SIMILARITY_THRESHOLD,
                           rank_by: str = "최고 유사도", top_n: int = TOP_N_RESEARCHERS) -> dict:
    df = state.df
    work = df.copy()
    work["유사도"] = sims
    work["임계값이상"] = work["유사도"] >= threshold

    counts_above = work.groupby("연구자번호")["임계값이상"].sum()
    idxmax_all = work.groupby("연구자번호")["유사도"].idxmax()
    rep = work.loc[
        idxmax_all, ["연구자번호", "연구책임자명", "주관기관명", "특구지역", "과제명", "유사도"],
    ].rename(columns={"과제명": "대표유사과제명"}).set_index("연구자번호")
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
    selected["연구책임자명_표시"] = selected.apply(
        lambda r: display_researcher_name(r, state.dup_pairs), axis=1
    )
    table = [
        {
            "연구책임자명": row["연구책임자명_표시"], "주관기관명": row["주관기관명"],
            "특구지역": row["특구지역"], "대표유사과제명": row["대표유사과제명"],
            "유사도": round(float(row["유사도"]), 3), "과제수": int(row["과제수"]),
        }
        for _, row in selected.iterrows()
    ]
    return {"reference_only": reference_only, "table": table}
```

- [ ] **Step 3: `main.py` — FastAPI 앱 (엔드포인트는 Task 2에서 채움, 여기서는 기동만)**

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import pipeline

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

state: pipeline.PipelineState | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global state
    state = pipeline.load_and_build()
    print(f"파이프라인 로드 완료: {len(state.df)}건 / {state.df['주관기관명'].nunique()}개 기관")
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
```

- [ ] **Step 4: 기동 확인**

```powershell
cd C:\project
C:\project\.venv\Scripts\python.exe -m uvicorn 03_webapp.backend.main:app --port 8000 &
Start-Sleep -Seconds 3
Invoke-WebRequest http://127.0.0.1:8000/static/ -UseBasicParsing | Select-Object StatusCode
```

Expected: 서버가 콘솔에 `파이프라인 로드 완료: 1680건 / 27개 기관`을 출력하며 기동. (참고: Python 패키지
이름은 숫자로 시작할 수 없어 `03_webapp`을 모듈 경로로 바로 못 쓸 수 있다 — 실제 실행 시 에러가 나면
`python -m uvicorn` 대신 `cd 03_webapp && uvicorn backend.main:app`처럼 작업 디렉터리를 옮겨 실행하거나,
`sys.path` 조정 없이 되는 방식을 실제로 확인해서 이 Step의 명령을 그에 맞게 고쳐라 — 여기 적힌 커맨드가
안 되면 이 계획의 오류이니 동작하는 방식으로 대체하고 보고서에 기록한다.)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt 03_webapp/backend/pipeline.py 03_webapp/backend/main.py 03_webapp/backend/__init__.py
git commit -m "feat(webapp): add FastAPI backend pipeline module (ported from notebook algorithm)"
```

---

### Task 2: `/api/search`, `/api/clusters` 엔드포인트

**Files:**
- Modify: `03_webapp/backend/main.py`

**Interfaces:**
- Consumes: `pipeline.search_similar_tasks`, `pipeline.recommend_researchers`, `pipeline.get_cluster_points`
- Produces: `GET /api/clusters` → `{"points": [...], "n_clusters": 6}`. `GET /api/search?query=...&threshold=
  0.15&rank_by=최고 유사도` → `{"empty_corpus", "blank_query", "reference_only", "count", "orgs", "tasks",
  "cluster", "query_coord", "researchers_reference_only", "researchers"}` (주의: `pipeline.search_similar_tasks`
  가 반환하는 raw `sims` numpy 배열은 이 엔드포인트에서 `recommend_researchers`에 넘기는 용도로만 쓰고,
  **최종 JSON 응답에는 포함하지 않는다** — numpy 배열은 JSON 직렬화가 안 되고, 1,680개 부동소수를
  응답에 넣을 이유도 없다).

- [ ] **Step 1: 엔드포인트 추가**

```python
from fastapi import Query

from . import pipeline as pipeline_module  # 이미 위에서 pipeline as pipeline로 import했다면 재사용


@app.get("/api/clusters")
def get_clusters():
    points = pipeline.get_cluster_points(state)
    return {"points": points, "n_clusters": pipeline.N_CLUSTERS}


@app.get("/api/search")
def get_search(
    query: str = Query(default=""),
    threshold: float = Query(default=pipeline.SIMILARITY_THRESHOLD),
    rank_by: str = Query(default="최고 유사도"),
):
    result = pipeline.search_similar_tasks(state, query, threshold=threshold)

    if result.get("blank_query") or result.get("empty_corpus"):
        return {**result, "researchers_reference_only": None, "researchers": []}

    sims = result.pop("sims")
    rec = pipeline.recommend_researchers(state, sims, threshold=threshold, rank_by=rank_by)
    return {
        **result,
        "researchers_reference_only": rec["reference_only"],
        "researchers": rec["table"],
    }
```

- [ ] **Step 2: 수동 검증 — 서버 기동 후 curl/Invoke-RestMethod로 실제 호출**

```powershell
# (서버가 Task 1 Step 4처럼 떠 있는 상태에서)
$r1 = Invoke-RestMethod "http://127.0.0.1:8000/api/clusters"
Write-Output "clusters: $($r1.points.Count) points, $($r1.n_clusters) clusters"
# Expected: clusters: 1680 points, 6 clusters

foreach ($q in @("인공지능 기반 이미지 분석 기술 개발","이차전지 소재 개발 연구","탄소중립 에너지 저장 시스템 개발")) {
    $r = Invoke-RestMethod "http://127.0.0.1:8000/api/search?query=$([uri]::EscapeDataString($q))"
    Write-Output "$q -> count=$($r.count) tasks=$($r.tasks.Count) researchers=$($r.researchers.Count)"
}
# Expected: 세 문장 모두 count > 0 (임계값 0.15에서 30/8/7건 전후 — 노트북에서 실측한 값과 일치해야 함)

$rBlank = Invoke-RestMethod "http://127.0.0.1:8000/api/search?query="
Write-Output "blank -> blank_query=$($rBlank.blank_query)"
# Expected: blank_query=True, researchers=[] (에러 없이)

$rEdge = Invoke-RestMethod "http://127.0.0.1:8000/api/search?query=$([uri]::EscapeDataString('가'))"
Write-Output "'가' -> reference_only=$($rEdge.reference_only)"
# Expected: 에러 없이 reference_only=True
```

Expected: 위 모든 호출이 500 에러 없이, 노트북에서 이미 실측한 것과 같은 건수 범위로 응답.

- [ ] **Step 3: 랭킹 드롭다운 9회 조합 확인**

```powershell
$queries = @("인공지능 기반 이미지 분석 기술 개발","이차전지 소재 개발 연구","탄소중립 에너지 저장 시스템 개발")
$ranks = @("최고 유사도","유사 과제 건수","합산 점수")
foreach ($q in $queries) {
    foreach ($rk in $ranks) {
        $r = Invoke-RestMethod "http://127.0.0.1:8000/api/search?query=$([uri]::EscapeDataString($q))&rank_by=$([uri]::EscapeDataString($rk))"
        Write-Output "$q | $rk -> researchers=$($r.researchers.Count) ref_only=$($r.researchers_reference_only)"
    }
}
```

Expected: 9줄 모두 `researchers >= 1`, 에러 없음.

- [ ] **Step 4: Commit**

```bash
git add 03_webapp/backend/main.py
git commit -m "feat(webapp): add /api/clusters and /api/search endpoints"
```

---

### Task 3: 프론트엔드 정적 뼈대 (HTML/CSS, 목업 시각 디자인 재현)

**Files:**
- Create: `03_webapp/frontend/index.html`
- Create: `03_webapp/frontend/styles.css`
- (이미 존재) `03_webapp/frontend/fonts/NanumSquareOTF_ac{L,R,B,EB}.otf` — 이 계획 작성 시점에 목업
  번들에서 이미 복사해둠

**Interfaces:**
- Produces: 화면1(입력행 + 통계 카드 3개 + 유사 과제 표 + 연구자 추천 표) + 화면2(SVG 산점도 + 범례)의
  정적 마크업. `id`가 붙은 요소들은 Task 4의 JS가 그대로 사용: `#topic-input`, `#rank-select`,
  `#search-btn`, `#stat-cluster`, `#stat-count`, `#stat-orgs`, `#task-table-body`, `#task-table-note`,
  `#researcher-table-body`, `#researcher-note`, `#cluster-svg`, `#cluster-legend`, `#result-banner`.

- [ ] **Step 1: `styles.css` 작성** (목업의 인라인 스타일에서 색상·타이포·spacing 토큰을 뽑아 재사용
  가능한 CSS로 정리 — 목업 원본의 `:root` 변수, 폰트, 배경색, 카드 스타일, 표 그리드를 그대로 옮긴다)

```css
@font-face { font-family: NanumSquare; src: url("fonts/NanumSquareOTF_acL.otf") format("opentype"); font-weight: 300; font-display: swap; }
@font-face { font-family: NanumSquare; src: url("fonts/NanumSquareOTF_acR.otf") format("opentype"); font-weight: 400; font-display: swap; }
@font-face { font-family: NanumSquare; src: url("fonts/NanumSquareOTF_acB.otf") format("opentype"); font-weight: 700; font-display: swap; }
@font-face { font-family: NanumSquare; src: url("fonts/NanumSquareOTF_acEB.otf") format("opentype"); font-weight: 800; font-display: swap; }

:root {
  --mint: #00C08B; --mint-soft: #A5EFD3; --mint-tint: #EEFBF6;
  --ink: #1B1D1F; --body-c: #4A4F52; --muted: #8B9296; --line: #E4E7E8;
}
* { box-sizing: border-box; }
body { margin: 0; background: #F7F8F8; font-family: NanumSquare, system-ui, sans-serif; color: var(--ink); }

.header { display: flex; align-items: center; justify-content: space-between; height: 64px; padding: 0 40px; background: #fff; border-bottom: 1px solid var(--line); }
.header-title { font-weight: 800; font-size: 15px; letter-spacing: -0.3px; }
.header-sub { font-size: 12px; color: var(--muted); padding-left: 12px; border-left: 1px solid var(--line); }

.page { max-width: 1200px; margin: 0 auto; padding: 40px 40px 80px; display: flex; flex-direction: column; gap: 28px; }
.section-title { display: flex; align-items: baseline; gap: 12px; }
.section-num { font-size: 12px; font-weight: 800; color: #00A87A; letter-spacing: 1px; }
.section-heading { font-size: 22px; font-weight: 800; letter-spacing: -0.6px; }
.section-desc { font-size: 13px; color: var(--muted); }

.card { background: #fff; border: 1px solid var(--line); border-radius: 12px; }
.search-card { padding: 24px; display: flex; align-items: flex-end; gap: 12px; }
.field { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.field label { font-size: 12px; font-weight: 700; color: var(--body-c); }
.field input, .field select {
  height: 48px; padding: 0 14px; font-family: NanumSquare, system-ui, sans-serif; font-size: 14px;
  color: var(--ink); background: #fff; border: 1px solid var(--line); border-radius: 8px; outline: none;
}
.field input:focus, .field select:focus { border-color: var(--mint); box-shadow: 0 0 0 3px rgba(0,192,139,.15); }
.field-rank { width: 200px; }
#search-btn {
  height: 48px; min-width: 104px; padding: 0 20px; border: none; border-radius: 8px;
  background: var(--mint); color: #fff; font-family: NanumSquare, system-ui, sans-serif;
  font-size: 14px; font-weight: 700; cursor: pointer;
}
#search-btn:active { background: #00A87A; }

.stat-grid { display: grid; grid-template-columns: 200px 200px 1fr; gap: 16px; }
.stat-card { padding: 18px 20px; display: flex; flex-direction: column; gap: 6px; }
.stat-label { font-size: 12px; color: var(--muted); font-weight: 700; }
.stat-value { font-size: 34px; font-weight: 800; letter-spacing: -1.5px; line-height: 1; }
.stat-value.accent { color: #00A87A; }
.org-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.org-tag { font-size: 12.5px; font-weight: 700; color: var(--ink); background: #F1F3F3; border-radius: 999px; padding: 5px 11px; }

.table-card { overflow: hidden; }
.table-head { display: flex; align-items: baseline; justify-content: space-between; padding: 20px 24px 16px; }
.table-head-left { display: flex; align-items: baseline; gap: 10px; }
.table-head-title { font-size: 15px; font-weight: 800; letter-spacing: -0.3px; }
.table-head-sub { font-size: 12px; color: var(--muted); }
.rank-badge { font-size: 12px; color: var(--body-c); background: var(--mint-tint); border: 1px solid #CFF0E4; border-radius: 999px; padding: 5px 12px; font-weight: 700; }

.task-row { display: grid; grid-template-columns: 1fr 200px 68px 108px 92px; align-items: center; padding: 14px 24px; border-bottom: 1px solid #F1F3F3; }
.task-row-head { border-bottom: 1px solid var(--line); padding: 0 24px 8px; }
.researcher-row { display: grid; grid-template-columns: 132px 180px 90px 1fr 100px 72px; align-items: center; padding: 13px 24px; border-bottom: 1px solid #F1F3F3; }
.researcher-row-head { border-bottom: 1px solid var(--line); padding: 0 24px 8px; }
.col-label { font-size: 11.5px; font-weight: 700; color: var(--muted); }
.cluster-badge { display: inline-block; font-size: 12px; font-weight: 800; color: #00694E; padding: 4px 10px; border-radius: 999px; background: var(--mint-tint); border: 1px solid #CFF0E4; }
.avatar { width: 26px; height: 26px; border-radius: 999px; background: var(--mint-soft); color: #00694E; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.researcher-name-cell { display: flex; align-items: center; gap: 9px; }

#result-banner { display: none; padding: 12px 24px; font-size: 13px; font-weight: 700; border-radius: 10px; }
#result-banner.reference { display: block; background: #FFF8E6; border: 1px solid #F5DFA0; color: #7A5B00; }
#result-banner.blank { display: block; background: #F1F3F3; border: 1px solid var(--line); color: var(--body-c); }

.map-card { padding: 24px; display: flex; gap: 24px; }
.map-svg-wrap { flex: 1; min-width: 0; }
.map-legend { width: 236px; display: flex; flex-direction: column; gap: 14px; }
.legend-row { display: flex; align-items: center; gap: 10px; }
.legend-dot { width: 10px; height: 10px; border-radius: 999px; flex: none; }
.legend-label { font-size: 13px; font-weight: 700; width: 90px; }
```

- [ ] **Step 2: `index.html` 작성** (정적 마크업, 표 본문은 빈 상태로 두고 Task 4의 JS가 채움)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>R&D 특구 유사 과제 검색</title>
<link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <div class="header">
    <div style="display:flex;align-items:center;gap:12px">
      <span class="header-title">R&amp;D 특구 유사 과제 검색</span>
      <span class="header-sub">공개데이터 기반 프로토타입</span>
    </div>
    <div class="header-sub" style="border-left:none">TF-IDF · KMeans(6) · TruncatedSVD</div>
  </div>

  <div class="page">
    <div class="section-title">
      <span class="section-num">01</span>
      <span class="section-heading">유사 과제 검색</span>
      <span class="section-desc">주제를 입력하면 임계값 이상으로 유사한 기존 과제와 수행 연구자를 보여줍니다.</span>
    </div>

    <div class="card search-card">
      <div class="field">
        <label for="topic-input">과제 주제:</label>
        <input id="topic-input" type="text" placeholder="준비 중인 과제의 주제를 입력하세요">
      </div>
      <div class="field field-rank">
        <label for="rank-select">랭킹 기준:</label>
        <select id="rank-select">
          <option value="최고 유사도">최고 유사도</option>
          <option value="유사 과제 건수">유사 과제 건수</option>
          <option value="합산 점수">합산 점수</option>
        </select>
      </div>
      <button id="search-btn">검색</button>
    </div>

    <div id="result-banner"></div>

    <div class="stat-grid">
      <div class="card stat-card">
        <div class="stat-label">추정 클러스터</div>
        <div class="stat-value accent" id="stat-cluster">–</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">유사 과제 건수</div>
        <div class="stat-value" id="stat-count">–</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">수행 기관</div>
        <div class="org-tags" id="stat-orgs"></div>
      </div>
    </div>

    <div class="card table-card">
      <div class="table-head">
        <div class="table-head-left">
          <span class="table-head-title">유사 과제</span>
          <span class="table-head-sub" id="task-table-note">유사도 상위 5건</span>
        </div>
      </div>
      <div class="task-row task-row-head">
        <div class="col-label">과제명</div><div class="col-label">주관기관명</div>
        <div class="col-label">연도</div><div class="col-label">유사도</div><div class="col-label">클러스터</div>
      </div>
      <div id="task-table-body"></div>
    </div>

    <div class="card table-card">
      <div class="table-head">
        <div class="table-head-left">
          <span class="table-head-title">연구자 추천</span>
          <span class="table-head-sub">상위 5명</span>
        </div>
        <span class="rank-badge" id="researcher-note">정렬 기준: 최고 유사도</span>
      </div>
      <div class="researcher-row researcher-row-head">
        <div class="col-label">연구책임자명</div><div class="col-label">주관기관명</div>
        <div class="col-label">특구지역</div><div class="col-label">대표 유사 과제명</div>
        <div class="col-label">유사도</div><div class="col-label">과제수</div>
      </div>
      <div id="researcher-table-body"></div>
      <div style="padding:14px 24px;font-size:12px;color:var(--muted)">
        동명이인(이름·기관 동일)은 연구자번호 뒷 4자리를 괄호로 표기합니다.
      </div>
    </div>

    <div style="height:1px;background:var(--line);margin:12px 0"></div>

    <div class="section-title">
      <span class="section-num">02</span>
      <span class="section-heading">전체 클러스터 지도</span>
      <span class="section-desc">TruncatedSVD 2차원 투영 · KMeans 6개 클러스터</span>
    </div>

    <div class="card map-card">
      <div class="map-svg-wrap">
        <svg id="cluster-svg" viewBox="0 0 880 520" style="width:100%;height:auto;display:block"></svg>
      </div>
      <div class="map-legend">
        <div class="stat-label">클러스터 범례</div>
        <div id="cluster-legend"></div>
      </div>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: 브라우저 없이 정적 파일 서빙 확인**

```powershell
Invoke-WebRequest http://127.0.0.1:8000/static/index.html -UseBasicParsing | Select-Object StatusCode, @{n='len';e={$_.RawContentLength}}
Invoke-WebRequest http://127.0.0.1:8000/static/styles.css -UseBasicParsing | Select-Object StatusCode
```

Expected: 둘 다 200. (아직 `app.js`는 Task 4에서 만들어지므로 `index.html`이 그 스크립트 태그로 404를
내는 건 이 시점엔 정상 — Task 4에서 해소됨)

- [ ] **Step 4: Commit**

```bash
git add 03_webapp/frontend/index.html 03_webapp/frontend/styles.css 03_webapp/frontend/fonts
git commit -m "feat(webapp): add static frontend shell reproducing the Claude Design mockup's visuals"
```

---

### Task 4: 프론트엔드 JS — API 연동 + 화면1/화면2 렌더링

**Files:**
- Create: `03_webapp/frontend/app.js`

**Interfaces:**
- Consumes: `/api/clusters`, `/api/search` (Task 2)
- Produces: 브라우저에서 실행되는 전체 인터랙션. 전역 함수 없음 — 즉시실행 스크립트.

- [ ] **Step 1: `app.js` 작성**

```javascript
const CLUSTER_COLORS = ["#1B1D1F", "#6E7579", "#B9BEC1", "#00C08B", "#00755C", "#A5EFD3"];

const topicInput = document.getElementById("topic-input");
const rankSelect = document.getElementById("rank-select");
const searchBtn = document.getElementById("search-btn");
const banner = document.getElementById("result-banner");
const statCluster = document.getElementById("stat-cluster");
const statCount = document.getElementById("stat-count");
const statOrgs = document.getElementById("stat-orgs");
const taskBody = document.getElementById("task-table-body");
const taskNote = document.getElementById("task-table-note");
const researcherBody = document.getElementById("researcher-table-body");
const researcherNote = document.getElementById("researcher-note");
const svg = document.getElementById("cluster-svg");
const legendEl = document.getElementById("cluster-legend");

let clusterPoints = [];
let xScale = (x) => x, yScale = (y) => y;

function fitScales(points) {
  const xs = points.map(p => p.x), ys = points.map(p => p.y);
  const [xMin, xMax] = [Math.min(...xs), Math.max(...xs)];
  const [yMin, yMax] = [Math.min(...ys), Math.max(...ys)];
  const pad = 40;
  xScale = (x) => pad + ((x - xMin) / (xMax - xMin || 1)) * (880 - pad * 2);
  yScale = (y) => pad + ((y - yMin) / (yMax - yMin || 1)) * (520 - pad * 2);
}

function renderClusterMap(highlight) {
  svg.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const p of clusterPoints) {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", xScale(p.x)); c.setAttribute("cy", yScale(p.y));
    c.setAttribute("r", "4"); c.setAttribute("fill", CLUSTER_COLORS[p.cluster] || "#999");
    c.setAttribute("opacity", "0.75");
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${p.과제명} | ${p.주관기관명} | ${p.특구지역} | 클러스터 ${p.cluster}`;
    c.appendChild(title);
    frag.appendChild(c);
  }
  svg.appendChild(frag);

  if (highlight) {
    const hx = xScale(highlight.x), hy = yScale(highlight.y);
    const star = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    star.setAttribute("cx", hx); star.setAttribute("cy", hy); star.setAttribute("r", "9");
    star.setAttribute("fill", "#1B1D1F"); star.setAttribute("stroke", "#fff"); star.setAttribute("stroke-width", "2");
    svg.appendChild(star);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", hx + 14); label.setAttribute("y", hy + 4);
    label.setAttribute("fill", "#1B1D1F"); label.setAttribute("font-size", "13"); label.setAttribute("font-weight", "800");
    label.textContent = `내 주제 (클러스터 ${highlight.cluster})`;
    svg.appendChild(label);
  }
}

function renderLegend(nClusters) {
  legendEl.innerHTML = "";
  for (let i = 0; i < nClusters; i++) {
    const row = document.createElement("div");
    row.className = "legend-row";
    row.innerHTML = `<span class="legend-dot" style="background:${CLUSTER_COLORS[i]}"></span><span class="legend-label">클러스터 ${i}</span>`;
    legendEl.appendChild(row);
  }
}

async function loadClusters() {
  const res = await fetch("/api/clusters");
  const data = await res.json();
  clusterPoints = data.points;
  fitScales(clusterPoints);
  renderLegend(data.n_clusters);
  renderClusterMap(null);
}

function renderBanner(state) {
  banner.className = "";
  if (state === "blank") {
    banner.textContent = "검색어를 입력해주세요.";
    banner.className = "blank";
  } else if (state === "empty_corpus") {
    banner.textContent = "특구 소속 기관이 수행한 과제 데이터가 없습니다.";
    banner.className = "blank";
  } else if (state === "reference") {
    banner.textContent = "정확히 일치하는 유사 과제를 찾지 못했습니다. 아래는 유사도가 가장 높았던 3건입니다(참고용).";
    banner.className = "reference";
  } else {
    banner.style.display = "none";
  }
}

function renderTaskTable(result) {
  taskBody.innerHTML = "";
  taskNote.textContent = result.reference_only ? "참고용 상위 3건" : "유사도 상위 5건";
  for (const t of result.tasks) {
    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
      <div>${t.과제명}</div>
      <div>${t.주관기관명}</div>
      <div>${t.선정년도}</div>
      <div>${t.유사도.toFixed(3)}</div>
      <div><span class="cluster-badge">${t.클러스터}</span></div>`;
    taskBody.appendChild(row);
  }
}

function renderResearcherTable(result) {
  researcherBody.innerHTML = "";
  researcherNote.textContent = result.researchers_reference_only
    ? "참고용 — 임계값 미달"
    : `정렬 기준: ${rankSelect.value}`;
  for (const p of result.researchers) {
    const row = document.createElement("div");
    row.className = "researcher-row";
    row.innerHTML = `
      <div class="researcher-name-cell"><span class="avatar">${p.연구책임자명.slice(0, 1)}</span><span>${p.연구책임자명}</span></div>
      <div>${p.주관기관명}</div>
      <div>${p.특구지역}</div>
      <div>${p.대표유사과제명}</div>
      <div>${p.유사도.toFixed(3)}</div>
      <div>${p.과제수}</div>`;
    researcherBody.appendChild(row);
  }
}

async function runSearch() {
  const query = topicInput.value;
  const rankBy = rankSelect.value;
  const url = `/api/search?query=${encodeURIComponent(query)}&rank_by=${encodeURIComponent(rankBy)}`;
  const res = await fetch(url);
  const result = await res.json();

  if (result.blank_query) { renderBanner("blank"); taskBody.innerHTML = ""; researcherBody.innerHTML = ""; statCluster.textContent = "–"; statCount.textContent = "–"; statOrgs.innerHTML = ""; renderClusterMap(null); return; }
  if (result.empty_corpus) { renderBanner("empty_corpus"); return; }

  renderBanner(result.reference_only ? "reference" : null);
  statCluster.textContent = result.cluster;
  statCount.textContent = result.reference_only ? "0" : result.count;
  statOrgs.innerHTML = (result.orgs || []).map(o => `<span class="org-tag">${o}</span>`).join("");
  renderTaskTable(result);
  renderResearcherTable(result);
  renderClusterMap({ ...result.query_coord, cluster: result.cluster });
}

searchBtn.addEventListener("click", runSearch);
rankSelect.addEventListener("change", () => { if (topicInput.value.trim()) runSearch(); });
topicInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });

loadClusters();
```

- [ ] **Step 2: 브라우저 없이 스크립트 서빙 + 문법 확인**

```powershell
Invoke-WebRequest http://127.0.0.1:8000/static/app.js -UseBasicParsing | Select-Object StatusCode
C:\project\.venv\Scripts\python.exe -c "import subprocess; print('app.js is plain text, syntax checked via node if available')"
node --check C:\project\03_webapp\frontend\app.js 2>&1  # node가 없으면 이 줄만 건너뛰고 다음 Step에서 실제 브라우저로 확인
```

Expected: `app.js` 200 응답. `node --check`이 있으면 문법 에러 없이 종료(node 없으면 무시하고 Step 3으로).

- [ ] **Step 3: Commit**

```bash
git add 03_webapp/frontend/app.js
git commit -m "feat(webapp): wire frontend to /api/search and /api/clusters"
```

---

### Task 5: 완료조건 검증 + 실행 문서화

**Files:**
- Create: `03_webapp/README.md`
- Modify: `HANDOFF.md`, `PROJECT_PLAN.md` (2단계 진행 상태 반영)

**Interfaces:**
- 없음(문서 + 최종 검증)

- [ ] **Step 1: `03_webapp/README.md` 작성 — 실행 방법**

```markdown
# 2단계 웹앱 실행 방법

## 준비
`.venv`에 fastapi/uvicorn이 설치되어 있어야 한다 (루트의 `requirements.txt` 참고).

## 서버 실행
'03_webapp' 디렉터리를 작업 디렉터리로 두고 다음을 실행한다(패키지 이름이 숫자로 시작해 프로젝트
루트에서 모듈 경로로 바로 실행이 안 될 수 있어, 실제로 되는 방식을 아래에 기록한다 — Task 1에서 확인한
정확한 커맨드로 교체):

```powershell
cd C:\project\03_webapp
C:\project\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

브라우저에서 http://127.0.0.1:8000/static/index.html 접속.

## 데이터
서버 시작 시 `01_data/`의 CSV 2개를 읽어 메모리에 파이프라인을 한 번 구축한다. DB나 외부 저장소 없음.
```

(실제 실행 커맨드가 이것과 다르게 확인됐다면 이 문서를 그 내용으로 갱신한다.)

- [ ] **Step 2: 완료조건 4개 실제 브라우저 확인 안내 — 이 Step은 사람이 직접 한다**

이 계획을 실행하는 에이전트는 브라우저가 없다. 아래 4가지는 반드시 사용자가 직접
`http://127.0.0.1:8000/static/index.html`을 열어 확인해야 하며, 에이전트는 이 사실을 보고서에
명시하고 "완료"라고 주장하지 않는다:

1. 예시 주제 3문장을 입력창에 입력 → 결과 표에 1건 이상
2. 유사 과제 표 한 행의 클러스터 번호와, 화면2 지도에서 그 색의 점이 실제로 있는지 대조
3. 입력창을 비우거나 한 글자만 넣고 검색 → 에러 화면(브라우저 콘솔 에러/빨간 화면) 없음
4. 예시 3개 × 랭킹 드롭다운 3개 = 9회 전환 → 에러 없이 표가 바뀜

에이전트가 실제로 할 수 있는 것: Task 2에서 이미 API 레벨로 9회 조합과 엣지 케이스를 검증했으므로,
그 결과를 근거로 "API는 검증됨, 브라우저 시각 확인은 사람이 할 차례"라고 명확히 구분해서 보고한다.

- [ ] **Step 3: `HANDOFF.md`/`PROJECT_PLAN.md` 갱신**

2단계(웹앱) 진행 상태, 실행 방법, 남은 사람 확인 사항(Step 2)을 반영한다. 정확한 문구는 실행 시점의
실제 상태에 맞춰 작성한다(이 계획이 완료된 시점에 맞게).

- [ ] **Step 4: Commit**

```bash
git add 03_webapp/README.md HANDOFF.md PROJECT_PLAN.md
git commit -m "docs(webapp): add run instructions, update handoff for stage-2 completion"
```
