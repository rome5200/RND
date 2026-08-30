from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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


# ── A.2 위험도 버킷 (규칙 기반, 새 모델 없음) ─────────────────────────────
# 실측 캘리브레이션(2026-08-25 재측정): 예시 3문장 count=30/8/7(TF-IDF)~37/26/11(하이브리드),
# 최고유사도 0.22~0.42. 과거 인용된 211/104/46은 이 데이터에서 재현되지 않아 폐기.
# RISK_SIM_HIGH는 임베딩 게이트(0.6) 영향으로 하이브리드 top_sim이 더 높게 나올 수 있어
# _calibrate_risk.py로 재확인 권장.
RISK_COUNT_HIGH = 20     # count "많음" 기준
RISK_SIM_HIGH = 0.50     # 최고유사도 "높음" 기준 (잠정 — 캘리브레이션으로 확정)


def _risk_bucket(count: int, top_sim, reference_only: bool) -> dict:
    """화면에 이미 나온 count/최고유사도를 요약하는 참고용 규칙 지표(예측 아님)."""
    if reference_only or top_sim is None:
        return {"level": "판단 보류", "reason": "유사 사례 부족 — 임계값 이상 매칭 없음"}
    count_high = count >= RISK_COUNT_HIGH
    sim_high = top_sim >= RISK_SIM_HIGH
    level = "높음" if (count_high and sim_high) else ("중간" if (count_high or sim_high) else "낮음")
    return {
        "level": level,
        "reason": f"유사 과제 {count}건, 최고 유사도 {top_sim:.3f} 기준 — 참고용 규칙 판정",
    }


# 모든 상태에서 존재하는 검색 응답 기본값 (A.1 envelope 균일성) — dup/risk 확장 필드 포함
_TASK_DEFAULTS = {
    "cluster": None, "query_coord": None, "count": 0, "orgs": [],
    "tasks": [], "reference_only": False,
    "researchers_reference_only": None, "researchers": [],
    "risk_bucket": None,
    "duplication_risk": False, "risk_count": 0, "institution_count": 0,
    "researcher_count": 0, "duplication_tasks": [],
}


@app.get("/api/clusters")
def get_clusters():
    points = pipeline.get_cluster_points(state)
    return {
        "points": points,
        "n_clusters": pipeline.N_CLUSTERS,
        "region_crosstab": pipeline.cluster_region_crosstab(state),  # A.3 화면2 크로스탭(additive)
    }


@app.get("/")
def read_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/search")
def get_search(
    query: str = Query(default=""),
    threshold: float = Query(default=pipeline.SIMILARITY_THRESHOLD),
    rank_by: str = Query(default="최고 유사도"),
):
    result = pipeline.search_similar_tasks(state, query, threshold=threshold)

    # A.1 상태 판별자 — 다운스트림은 status 하나만 보면 됨 (boolean은 하위호환용)
    if result.get("empty_corpus"):
        status = "empty_corpus"
    elif result.get("blank_query"):
        status = "blank_query"
    elif result.get("reference_only"):
        status = "reference_only"
    else:
        status = "ok"

    envelope = {
        "status": status,
        "empty_corpus": status == "empty_corpus",
        "blank_query": status == "blank_query",
        "reference_only": status == "reference_only",
        **_TASK_DEFAULTS,
    }

    if status in ("empty_corpus", "blank_query"):
        return envelope

    sims = result.pop("sims")
    # pipeline은 매칭/참고 행을 "table" 키로 반환 — 이 엔드포인트 계약상 "tasks"로 노출
    tasks = result.pop("table")
    rec = pipeline.recommend_researchers(state, sims, threshold=threshold, rank_by=rank_by)
    dup = pipeline.detect_duplication_risk(state, sims)
    top_sim = tasks[0]["유사도"] if tasks else None
    envelope.update(
        cluster=result["cluster"], query_coord=result["query_coord"],
        count=result["count"], orgs=result["orgs"],
        reference_only=result["reference_only"], tasks=tasks,
        researchers_reference_only=rec["reference_only"], researchers=rec["table"],
        risk_bucket=_risk_bucket(result["count"], top_sim, result["reference_only"]),
        **dup,
    )
    return envelope


# ── A.2 에고 그래프 / 공백 탐지 (신규 엔드포인트, pipeline.py 불변) ──────────
def _build_ego_graph(query: str, top_n: int = 8,
                     threshold: float = pipeline.SIMILARITY_THRESHOLD) -> dict:
    """query · 유사과제 Top-N · 연구책임자 · 세부사업(예산 프로그램 분류)으로 에고 그래프를 조립.
    weak 판정: 매칭 과제가 ≤2건뿐인 세부사업 노드를 표시 — 규칙 기반, 값 발명 없음.
    주의: 세부사업명은 '연구 주제'가 아니라 예산 지원 프로그램 분류이므로 '연구 공백'이 아니라
    '소수 수행 사업유형'으로 해석해야 한다(과대해석 금지)."""
    df = state.df
    empty = {"nodes": [], "edges": [], "node_count": 0}
    if query is None or not query.strip():
        return {"blank_query": True, "empty_corpus": False, **empty}

    r = pipeline.search_similar_tasks(state, query, threshold=threshold)
    if r.get("empty_corpus"):
        return {"blank_query": False, "empty_corpus": True, **empty}

    sims = r["sims"]
    reference_only = bool(r.get("reference_only", False))
    idx = np.where(sims >= threshold)[0]
    if len(idx) == 0:
        idx = np.argsort(-sims)[:3]  # 참고용: 임계값 미달이면 상위 3건으로라도 그림
    else:
        idx = idx[np.argsort(-sims[idx])][:top_n]

    nodes = {"q": {"id": "q", "type": "query", "label": query.strip()}}
    edges = []
    subfield_hits = {}
    for i in idx:
        i = int(i)
        row = df.iloc[i]
        tid, rid = f"t{i}", f"r{int(row['연구자번호'])}"
        nodes[tid] = {"id": tid, "type": "task", "label": str(row["과제명"]),
                      "year": int(row["선정년도"]), "org": str(row["주관기관명"])}
        nodes.setdefault(rid, {"id": rid, "type": "researcher",
                               "label": pipeline.display_researcher_name(row, state.dup_pairs)})
        edges.append({"src": "q", "dst": tid, "kind": "유사도", "w": round(float(sims[i]), 3)})
        edges.append({"src": rid, "dst": tid, "kind": "수행"})

        # 세부사업명 결측(1,680건 중 427건 = 25%)은 노드를 만들지 않는다 —
        # str(NaN)="nan"으로 처리하면 무관한 결측 과제들이 한 노드로 잘못 병합돼
        # 사업유형 판정(소수 수행)을 왜곡하기 때문.
        sf_val = row["세부사업명"]
        if sf_val == sf_val and str(sf_val).strip():   # NaN != NaN 이용 (pandas import 불필요)
            sf = str(sf_val).strip()
            sfid = "s_" + sf                            # 문자열을 직접 id로 (hash 충돌 원천 차단)
            nodes.setdefault(sfid, {"id": sfid, "type": "subfield", "label": sf})
            edges.append({"src": tid, "dst": sfid, "kind": "소속"})
            subfield_hits[sfid] = subfield_hits.get(sfid, 0) + 1

    for n in nodes.values():
        if n["type"] == "subfield":
            n["weak"] = subfield_hits.get(n["id"], 0) <= 2

    return {"blank_query": False, "empty_corpus": False, "reference_only": reference_only,
            "nodes": list(nodes.values()), "edges": edges, "node_count": len(nodes)}


@app.get("/api/ego_graph")
def get_ego_graph(query: str = Query(default=""), top_n: int = Query(default=8)):
    return _build_ego_graph(query, top_n=top_n)


# ── A.3 지역 기술편중 (신규 엔드포인트, pipeline.py에 독립 인덱스 추가) ──────────
@app.get("/api/region")
def get_region(
    query: str = Query(default=""),
    threshold: float = Query(default=pipeline.SIMILARITY_THRESHOLD),
):
    """전체 코퍼스(11,783) 대비 '유사 과제 중 특구소속 비율'과 특구별 분포 + 고정 편중지표(LQ).
    envelope 균일성(계약 §7): 모든 상태에서 동일 키 존재(비해당 시 null/0/[]). concentration은 항상 존재."""
    rb = pipeline.region_breakdown(state, query, threshold=threshold)

    if rb.get("empty_corpus"):
        status = "empty_corpus"
    elif rb.get("blank_query"):
        status = "blank_query"
    elif rb.get("reference_only"):
        status = "reference_only"
    else:
        status = "ok"

    return {
        "status": status,
        "empty_corpus": status == "empty_corpus",
        "blank_query": status == "blank_query",
        "reference_only": status == "reference_only",
        "total_matched": rb["total_matched"],
        "특구소속_matched": rb["특구소속_matched"],
        "특구소속_비율": rb["특구소속_비율"],
        "regions": rb["regions"],
        "top3": rb["top3"],
        "concentration": state.region_concentration,
        "scale_note": ("규모지표 = 특구별 입주기업 수(특구입주기업현황.csv). "
                       "특구통계조사총괄.csv는 연도별 전국 합계라 특구별 정규화 불가."),
    }
