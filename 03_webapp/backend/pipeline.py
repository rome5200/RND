"""웹앱 백엔드용 검색·클러스터링·연구자 추천 파이프라인.
02_notebook/similar_task_search.ipynb의 검증된 알고리즘을 API 서버용으로 독립 재구현한 것 — 노트북 파일
자체는 참조/수정하지 않는다."""
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

    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings = embedder.encode(df["과제명"].tolist(), normalize_embeddings=True)

    return PipelineState(
        df=df, vectorizer=vectorizer, tfidf_matrix=tfidf_matrix,
        svd=svd, coords=coords, kmeans=kmeans, dup_pairs=dup_pairs,
        embedder=embedder, embeddings=embeddings,
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
