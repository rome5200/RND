from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
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
        return {**result, "tasks": [], "researchers_reference_only": None, "researchers": []}

    sims = result.pop("sims")
    # pipeline.search_similar_tasks returns matched/reference rows under the "table" key;
    # the API response exposes them as "tasks" per this endpoint's documented contract.
    tasks = result.pop("table")
    rec = pipeline.recommend_researchers(state, sims, threshold=threshold, rank_by=rank_by)
    return {
        **result,
        "tasks": tasks,
        "researchers_reference_only": rec["reference_only"],
        "researchers": rec["table"],
    }
