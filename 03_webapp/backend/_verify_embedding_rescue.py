"""임베딩 보강 효과를 예시 3문장이 아니라 전체 1,680건 self-search + 전체 쌍 분포로 검증.
발표 중 사용 안 함 / 개발용. 실행: python -m 03_webapp.backend._verify_embedding_rescue

방법:
  A) 매칭 코퍼스 1,680건 각각을 "신규 검토 주제"로 가정해 자기 자신을 제외한 나머지와 비교.
     TF-IDF만 썼을 때 0건(reference_only)인 케이스 중 임베딩 결합으로 몇 건이 구제되는지 집계.
  B) 임베딩 코사인 유사도 전체 쌍(1,680x1,680, 대각선 제외 2,822,320쌍)의 분포를 내서
     EMBEDDING_SIMILARITY_THRESHOLD=0.6이 "무관한 쌍" 노이즈 플로어 대비 어디 있는지 확인.
"""
import numpy as np
from . import pipeline


def main():
    state = pipeline.load_and_build()
    df = state.df
    n = len(df)
    tfidf_matrix = state.tfidf_matrix
    embeddings = state.embeddings
    threshold = pipeline.SIMILARITY_THRESHOLD
    emb_threshold = pipeline.EMBEDDING_SIMILARITY_THRESHOLD

    # ── B) 전체 쌍 임베딩 유사도 분포 (대각선=자기자신 제외) ──
    full_sim = embeddings @ embeddings.T
    off_diag_mask = ~np.eye(n, dtype=bool)
    off_diag = full_sim[off_diag_mask]
    print("=== B) 임베딩 코사인 유사도 전체 쌍 분포 (대각선 제외, n=%d쌍) ===" % off_diag.size)
    for p in [50, 90, 95, 99, 99.9, 100]:
        print(f"  p{p}: {np.percentile(off_diag, p):.3f}")
    print(f"  0.6 이상인 쌍 비율: {(off_diag >= emb_threshold).mean()*100:.4f}%  "
          f"({(off_diag >= emb_threshold).sum()}건)")
    print(f"  0.15 이상인 쌍 비율(TF-IDF 임계값 기준): {(off_diag >= threshold).mean()*100:.2f}%")

    # ── A) 전체 1,680건 self-search: TF-IDF 단독 vs 하이브리드 ──
    tfidf_sim_all = (tfidf_matrix @ tfidf_matrix.T).toarray()
    np.fill_diagonal(tfidf_sim_all, 0.0)
    np.fill_diagonal(full_sim, 0.0)
    gated_emb = np.where(full_sim >= emb_threshold, full_sim, 0.0)
    hybrid_sim_all = np.maximum(tfidf_sim_all, gated_emb)

    tfidf_counts = (tfidf_sim_all >= threshold).sum(axis=1)
    hybrid_counts = (hybrid_sim_all >= threshold).sum(axis=1)

    zero_tfidf = tfidf_counts == 0
    rescued = zero_tfidf & (hybrid_counts > 0)

    print(f"\n=== A) 전체 {n}건 self-search (TF-IDF 단독 vs 하이브리드) ===")
    print(f"  TF-IDF 단독 0건(reference_only) 케이스: {zero_tfidf.sum()}건 ({zero_tfidf.mean()*100:.1f}%)")
    print(f"  그중 임베딩 결합으로 구제(count>0)된 케이스: {rescued.sum()}건 "
          f"({rescued.sum()/max(zero_tfidf.sum(),1)*100:.1f}% of 0건 케이스, "
          f"전체의 {rescued.mean()*100:.2f}%)")
    print(f"  TF-IDF count  median/mean: {np.median(tfidf_counts):.1f} / {tfidf_counts.mean():.2f}")
    print(f"  하이브리드 count median/mean: {np.median(hybrid_counts):.1f} / {hybrid_counts.mean():.2f}")

    if rescued.sum() > 0:
        rescue_sims = []
        for i in np.where(rescued)[0]:
            row = gated_emb[i]
            top = row.max()
            rescue_sims.append(top)
        rescue_sims = np.array(rescue_sims)
        print(f"  구제 케이스의 (임베딩) 최고유사도 median/min/max: "
              f"{np.median(rescue_sims):.3f} / {rescue_sims.min():.3f} / {rescue_sims.max():.3f}")


if __name__ == "__main__":
    main()
