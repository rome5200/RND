"""A.3 지역 기술편중 로직 회귀 검증 — 프로젝트 venv에서 실행:
    python -m 03_webapp.backend._verify_region   (또는 backend 폴더에서 python _verify_region.py)
실제 pipeline.load_and_build()로 상태를 만들어(임베딩 포함) region_breakdown/편중지표 불변식을 확인한다.
컨테이너 TF-IDF 전용 검증(2026-08-30)에서 이미 join=1680·정규화·LQ·envelope 통과를 확인했고,
이 스크립트는 임베딩 경로까지 포함한 엔드투엔드 재확인용이다."""
import sys
try:
    from . import pipeline as P            # 패키지로 실행
except ImportError:
    import pipeline as P                    # backend 폴더에서 직접 실행

fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond: fails.append(name)

print("파이프라인 로드 중(임베딩 계산 포함, 수십 초 소요)…")
state = P.load_and_build()

check("전체 코퍼스 = 11783", len(state.full_df) == 11783, str(len(state.full_df)))
check("특구소속 = 1680", int(state.full_df["특구소속"].sum()) == 1680)
check("규모표 6개 특구(강소 통합)", set(state.region_scale) == {"대덕","대구","광주","부산","전북","강소"}, str(state.region_scale))

conc = state.region_concentration
check("편중지표 6행", len(conc) == 6)
check("과제_비중 합 ≈ 1", abs(sum(r["과제_비중"] for r in conc) - 1) < 1e-3)
daegu = next(r for r in conc if r["특구"]=="대구")["집중도_LQ"]
busan = next(r for r in conc if r["특구"]=="부산")["집중도_LQ"]
check("LQ 대구 과집중>1.5 · 부산 과소<0.6", daegu > 1.5 and busan < 0.6, f"대구{daegu} 부산{busan}")
for r in conc: print("   ", r["특구"], "과제", r["과제수"], "기업", r["입주기업수"], "LQ", r["집중도_LQ"])

# 상태 4종 + 불변식
blank = P.region_breakdown(state, "  ")
check("blank_query envelope", blank["blank_query"] and blank["특구소속_비율"] is None and blank["regions"]==[])
nm = P.region_breakdown(state, "존재하지않을질의zzqxq", threshold=0.99)
check("reference_only(매칭0) envelope", nm["reference_only"] and nm["total_matched"]==0)
ok = P.region_breakdown(state, "인공지능 영상 진단")
check("특구소속_matched ≤ total_matched", ok["특구소속_matched"] <= ok["total_matched"], f'{ok["특구소속_matched"]}/{ok["total_matched"]}')
if ok["regions"]:
    check("regions count 합 = 특구소속_matched", sum(r["count"] for r in ok["regions"]) == ok["특구소속_matched"])
    check("top3 = regions[:3] & 내림차순", ok["top3"] == ok["regions"][:3])
print("  ok:", {k: ok[k] for k in ("total_matched","특구소속_matched","특구소속_비율")},
      [(r["특구"], r["count"]) for r in ok["regions"]])

print(("\n=== %d FAIL ===" % len(fails)) if fails else "\n=== ALL PASS ===")
sys.exit(1 if fails else 0)
