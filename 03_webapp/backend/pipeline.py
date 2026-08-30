"""웹앱 백엔드용 검색·클러스터링·연구자 추천 파이프라인.
02_notebook/similar_task_search.ipynb의 검증된 알고리즘을 API 서버용으로 독립 재구현한 것 — 노트북 파일
자체는 참조/수정하지 않는다."""
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parents[2] / "01_data"
SIMILARITY_THRESHOLD = 0.15
# 임베딩 코사인 유사도는 TF-IDF와 분포가 완전히 달라(무관한 질의도 노이즈 플로어가 0.15~0.5대) 같은
# 임계값을 못 씀. 실측 결과 무관한 질의는 0.6을 거의 못 넘고(1680건 중 1건), 진짜 의미적으로 겹치는
# 사례(예: "리튬이온 배터리 열폭주 억제" ↔ "이차전지 셀 발열 안정화")는 0.6대 초반~중반을 넘겨서
# 0.6으로 잡음 — 03_webapp/backend/_verify_embedding.py 분포 확인 결과 근거
EMBEDDING_SIMILARITY_THRESHOLD = 0.6
N_CLUSTERS = 6
TOP_N_TASKS = 5
TOP_N_RESEARCHERS = 5
RANK_OPTIONS = ["최고 유사도", "유사 과제 건수", "합산 점수"]
EMBEDDING_MODEL_NAME = "jhgan/ko-sroberta-multitask"
# 중복투자 위험 신호 — 유사도 0.75 이상 과제들 중 '다른 기관 × 선정년도 차이 2년 이내' 쌍에
# 속하는 과제를 위험군으로 판정. 검색 임계값(0.15)과 독립적으로 전체 sims 배열에 대해 계산한다.
DUPLICATION_SIMILARITY_THRESHOLD = 0.75
DUPLICATION_YEAR_WINDOW = 2  # 선정년도 차이 허용 범위(년)

@dataclass
class PipelineState:
    df: pd.DataFrame
    vectorizer: TfidfVectorizer
    tfidf_matrix: object
    svd: TruncatedSVD
    coords: np.ndarray
    kmeans: KMeans
    dup_pairs: set
    embedder: SentenceTransformer
    embeddings: np.ndarray
    # ── A.3 지역 기술편중용 전체 코퍼스 참조 인덱스 (기존 1,680 파이프라인과 독립, 계약 §7.4) ──
    full_df: pd.DataFrame
    full_vectorizer: TfidfVectorizer
    full_tfidf_matrix: object
    full_embeddings: np.ndarray
    region_scale: dict
    region_concentration: list


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


# ── A.3 지역 기술편중 분석 ────────────────────────────────────────────────
# 규모지표 출처 주의: 01_data/특구통계조사총괄.csv는 '구분'=연도(2005~2024)인 전국 연도별 합계
# 시계열이라 특구별 정규화에 못 쓴다. 특구별 규모 프록시는 특구입주기업현황.csv의 특구별
# 입주기업 수를 직접 집계해서 쓴다.

def _normalize_region(s) -> str:
    """'강소(경기안산)'·'강소(충북청주)' 등 세분 표기를 '강소'로 통합. 그 외는 그대로."""
    return re.sub(r"강소\(.*\)", "강소", str(s))


def _load_full_and_scale() -> tuple[pd.DataFrame, dict]:
    """전체 과제(보안 제외 11,783건)에 특구소속 여부·정규화 특구명을 부착하고,
    특구별 입주기업 수(규모 프록시)를 함께 반환한다. 기존 _load_joined_df와 독립."""
    companies = pd.read_csv(DATA_DIR / "특구입주기업현황.csv", encoding="cp949")
    companies = companies.rename(columns={"지역": "특구지역"})
    companies["특구_norm"] = companies["특구지역"].map(_normalize_region)
    companies["_key"] = companies["기관명"].str.strip()

    tasks_raw = pd.read_csv(DATA_DIR / "이알앤디_과제정보.csv", encoding="cp949")
    tasks = tasks_raw[tasks_raw["보안과제여부"] != "Y"].copy().reset_index(drop=True)
    assert len(tasks) == 11783, f"보안과제 제외 후 건수가 예상과 다름: {len(tasks)}"
    tasks["과제명"] = tasks["과제명"].fillna("")
    tasks["_key"] = tasks["주관기관명"].str.strip()

    key2region = companies.drop_duplicates(subset="_key").set_index("_key")["특구_norm"]
    tasks["특구_norm"] = tasks["_key"].map(key2region)
    tasks["특구소속"] = tasks["특구_norm"].notna()
    n_tukku = int(tasks["특구소속"].sum())
    assert n_tukku == 1680, f"특구소속 과제 수가 예상과 다름: {n_tukku}"

    region_scale = {k: int(v) for k, v in companies["특구_norm"].value_counts().items()}
    return tasks.drop(columns=["_key"]).reset_index(drop=True), region_scale


def _build_concentration(full_df: pd.DataFrame, region_scale: dict) -> list:
    """전체 특구소속 1,680건 기준의 고정 편중지표(입지계수 LQ). query와 무관한 구조 지표.
    LQ = (특구 과제 점유율) / (특구 입주기업 점유율). >1 과집중, <1 과소."""
    sub = full_df[full_df["특구소속"]]
    task_counts = sub["특구_norm"].value_counts()
    total_tasks = int(task_counts.sum())
    total_scale = sum(region_scale.values())
    rows = []
    for region, tc in task_counts.items():
        sc = region_scale.get(region, 0)
        task_share = tc / total_tasks if total_tasks else 0.0
        firm_share = sc / total_scale if total_scale else 0.0
        lq = (task_share / firm_share) if firm_share else None
        rows.append({
            "특구": region, "과제수": int(tc), "과제_비중": round(task_share, 4),
            "입주기업수": int(sc), "기업_비중": round(firm_share, 4),
            "집중도_LQ": round(lq, 3) if lq is not None else None,
        })
    rows.sort(key=lambda r: -r["과제수"])
    return rows


def region_breakdown(state: "PipelineState", query: str,
                     threshold: float = SIMILARITY_THRESHOLD, top_n: int = 6) -> dict:
    """전체 코퍼스(11,783)에 질의해 '유사 과제 중 특구소속 비율'과 특구별 분포를 낸다.
    A.1/A.2 검색(1,680 한정)과 독립 — count 등 기존 계약 필드 의미를 바꾸지 않는다."""
    fdf = state.full_df
    empty = {"total_matched": 0, "특구소속_matched": 0, "특구소속_비율": None,
             "regions": [], "top3": []}
    if len(fdf) == 0:
        return {"empty_corpus": True, "blank_query": False, "reference_only": False, **empty}
    if query is None or not query.strip():
        return {"empty_corpus": False, "blank_query": True, "reference_only": False, **empty}

    qv = state.full_vectorizer.transform([query])
    tfidf_sims = cosine_similarity(qv, state.full_tfidf_matrix).flatten()
    q_emb = state.embedder.encode([query], normalize_embeddings=True)[0]
    emb_sims = state.full_embeddings @ q_emb
    gated = np.where(emb_sims >= EMBEDDING_SIMILARITY_THRESHOLD, emb_sims, 0.0)
    sims = np.maximum(tfidf_sims, gated)

    matched = np.where(sims >= threshold)[0]
    total = int(len(matched))
    if total == 0:
        return {"empty_corpus": False, "blank_query": False, "reference_only": True, **empty}

    msub = fdf.iloc[matched]
    tukku = int(msub["특구소속"].sum())
    ratio = tukku / total
    regions = []
    if tukku > 0:
        vc = msub[msub["특구소속"]]["특구_norm"].value_counts()
        total_scale = sum(state.region_scale.values())
        for region, cnt in vc.items():
            sc = state.region_scale.get(region, 0)
            share = cnt / tukku
            firm_share = sc / total_scale if total_scale else 0.0
            lq = (share / firm_share) if firm_share else None
            regions.append({
                "특구": region, "count": int(cnt), "share": round(share, 4),
                "입주기업수": int(sc), "집중도_LQ": round(lq, 3) if lq is not None else None,
            })
        regions.sort(key=lambda r: -r["count"])
    return {
        "empty_corpus": False, "blank_query": False, "reference_only": False,
        "total_matched": total, "특구소속_matched": tukku,
        "특구소속_비율": round(ratio, 4),
        "regions": regions[:top_n], "top3": regions[:3],
    }


def cluster_region_crosstab(state: "PipelineState") -> dict:
    """1,680건을 KMeans 클러스터(0~5) × 정규화 특구로 교차집계. 화면2(클러스터 지도)의 _cluster를
    그대로 재사용하므로 화면1↔화면2 클러스터 일치 완료조건과 충돌하지 않는다. query 무관 고정."""
    df = state.df.copy()
    df["_rn"] = df["특구지역"].map(_normalize_region)
    regions = list(df["_rn"].value_counts().index)          # 총계 내림차순
    clusters = list(range(N_CLUSTERS))
    ct = df.groupby(["_cluster", "_rn"]).size().unstack(fill_value=0)
    matrix = [[int(ct.loc[c, r]) if (c in ct.index and r in ct.columns) else 0
               for r in regions] for c in clusters]
    return {
        "clusters": clusters,
        "regions": regions,
        "matrix": matrix,
        "row_totals": [int(sum(row)) for row in matrix],
        "col_totals": [int(df[df["_rn"] == r].shape[0]) for r in regions],
        "grand_total": int(len(df)),
    }


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

    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = embedder.encode(df["과제명"].tolist(), normalize_embeddings=True)

    # ── A.3 전체 코퍼스(11,783) 참조 인덱스 — 지역 기술편중 전용 (검색 파이프라인 불변) ──
    full_df, region_scale = _load_full_and_scale()
    full_vectorizer = TfidfVectorizer()
    full_tfidf_matrix = full_vectorizer.fit_transform(full_df["과제명"])
    full_embeddings = embedder.encode(full_df["과제명"].tolist(), normalize_embeddings=True)
    region_concentration = _build_concentration(full_df, region_scale)

    return PipelineState(
        df=df, vectorizer=vectorizer, tfidf_matrix=tfidf_matrix,
        svd=svd, coords=coords, kmeans=kmeans, dup_pairs=dup_pairs,
        embedder=embedder, embeddings=embeddings,
        full_df=full_df, full_vectorizer=full_vectorizer,
        full_tfidf_matrix=full_tfidf_matrix, full_embeddings=full_embeddings,
        region_scale=region_scale, region_concentration=region_concentration,
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
    tfidf_sims = cosine_similarity(query_vec, state.tfidf_matrix).flatten()

    query_embedding = state.embedder.encode([query], normalize_embeddings=True)[0]
    embedding_sims = state.embeddings @ query_embedding
    # 임베딩 유사도는 자체 임계값(EMBEDDING_SIMILARITY_THRESHOLD)을 넘을 때만 신뢰 —
    # 그 밑은 노이즈 플로어이므로 0으로 눌러서 TF-IDF 임계값(threshold)에 새어 들어가지 않게 함
    gated_embedding_sims = np.where(embedding_sims >= EMBEDDING_SIMILARITY_THRESHOLD, embedding_sims, 0.0)

    # 표면 단어가 겹치는 경우(TF-IDF)와 어휘는 달라도 의미가 겹치는 경우(임베딩) 중
    # 어느 한쪽이라도 강하게 유사하다고 판단하면 반영되도록 두 신호의 최댓값을 사용
    sims = np.maximum(tfidf_sims, gated_embedding_sims)

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

def detect_duplication_risk(
    state: PipelineState,
    sims: np.ndarray,
    sim_threshold: float = DUPLICATION_SIMILARITY_THRESHOLD,
    year_window: int = DUPLICATION_YEAR_WINDOW,
) -> dict:
    """유사도 sim_threshold 이상인 과제들 중, 서로 기관이 다르고 선정년도 차이가
    year_window 이내인 쌍에 한 번이라도 속하는 과제를 '중복투자 위험군'으로 집계한다.
    쌍 성립 조건상 위험군이 존재하면 관련 기관 수는 항상 2개 이상이다."""
    df = state.df
    empty = {
        "duplication_risk": False, "risk_count": 0,
        "institution_count": 0, "researcher_count": 0,
        "duplication_tasks": [],
    }

    high_idx = np.where(sims >= sim_threshold)[0]
    if len(high_idx) < 2:
        return empty

    sub = df.iloc[high_idx].copy()
    sub["_sim"] = sims[high_idx]
    years = sub["선정년도"].to_numpy()
    orgs = sub["주관기관명"].to_numpy()

    n = len(sub)
    risky = np.zeros(n, dtype=bool)
    for a in range(n):
        for b in range(a + 1, n):
            if orgs[a] != orgs[b] and abs(int(years[a]) - int(years[b])) <= year_window:
                risky[a] = risky[b] = True

    if not risky.any():
        return empty

    risk_rows = sub[risky].sort_values("_sim", ascending=False)
    tasks = [
        {
            "과제명": r["과제명"], "주관기관명": r["주관기관명"],
            "선정년도": int(r["선정년도"]), "유사도": round(float(r["_sim"]), 3),
            "연구책임자명": display_researcher_name(r, state.dup_pairs),
        }
        for _, r in risk_rows.iterrows()
    ]
    return {
        "duplication_risk": True,
        "risk_count": int(len(risk_rows)),
        "institution_count": int(risk_rows["주관기관명"].nunique()),
        "researcher_count": int(risk_rows["연구자번호"].nunique()),
        "duplication_tasks": tasks,
    }