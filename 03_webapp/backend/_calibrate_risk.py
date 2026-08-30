"""위험도 버킷 임계값 캘리브레이션 (발표 중 사용 안 함 / 개발용).

실제 하이브리드 파이프라인(TF-IDF + 임베딩 게이팅)으로 예시 3문장의
count / 최고유사도를 재측정해, main.py의 RISK_COUNT_HIGH / RISK_SIM_HIGH를 확정한다.

실행:
    $env:PYTHONIOENCODING="utf-8"          # (Windows)
    C:\\project\\.venv\\Scripts\\python.exe -m 03_webapp.backend._calibrate_risk
    # 또는 프로젝트 루트에서: python -m 03_webapp.backend._calibrate_risk

※ 2026-08-30 하이브리드 재측정(최종 확정): 예시 count=37/26/11, 최고유사도 0.763/0.843/0.728.
  → main.py RISK_COUNT_HIGH=26 / RISK_SIM_HIGH=0.76 반영 완료(api-contract-search.md §7.1 참고).
  과거 TF-IDF 단독 값(count=30/8/7, sim 0.22~0.42)과 그 이전 211/104/46은 모두 폐기됨.
"""
import numpy as np
from . import pipeline

EXAMPLES = [
    "인공지능 기반 이미지 분석 기술 개발",
    "이차전지 소재 개발 연구",
    "탄소중립 에너지 저장 시스템 개발",
]


def main():
    state = pipeline.load_and_build()
    rows = []
    for q in EXAMPLES:
        r = pipeline.search_similar_tasks(state, q)
        sims = r["sims"]
        count = int((sims >= pipeline.SIMILARITY_THRESHOLD).sum())
        top_sim = float(np.sort(sims)[-1])
        rows.append((q, count, top_sim))
        print(f"{q[:16]:18} | count={count:4d} | 최고유사도={top_sim:.3f}")

    counts = [c for _, c, _ in rows]
    sims = [s for _, _, s in rows]
    print("\n--- 캘리브레이션 참고값 ---")
    print(f"count  min/median/max = {min(counts)} / {int(np.median(counts))} / {max(counts)}")
    print(f"top_sim min/median/max = {min(sims):.3f} / {np.median(sims):.3f} / {max(sims):.3f}")
    print("\n권장 시작값 (예시가 낮음/중간/높음으로 갈리도록):")
    print(f"  RISK_COUNT_HIGH ≈ {int(np.median(counts))}  (median 근처)")
    print(f"  RISK_SIM_HIGH   ≈ {np.median(sims):.2f}  (median 근처)")
    print("→ 이 값을 main.py 상단 상수에 반영하고, 예시 3문장이 실제로 3개 버킷에 갈리는지 확인.")


if __name__ == "__main__":
    main()
