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
