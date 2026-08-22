# 작업 인수인계 — R&D 특구 유사 과제 검색 프로토타입

- 작성: 2026-08-22 (세션 리셋 직전 최종 갱신)
- 목적: 다음 세션에서 이 파일만 읽고 바로 이어서 작업할 수 있게 함

---

## 0. 지금 어디까지 왔나 (한 줄)

**1단계(Jupyter 노트북)는 완전히 끝났다(구현+리뷰+최종 통합 리뷰까지 전부 통과).** 사용자가 Claude
Design 목업을 받아온 뒤 **2단계(FastAPI + 정적 웹 프론트)로 범위를 확장하기로 결정**했고, 지금 그 구현
계획의 **Task 1~5(전체) 코드 구현은 끝났다.** 단, 완료조건 4개 중 브라우저에서 실제로 눈으로 확인해야
하는 부분(아래 2.5절)은 에이전트가 할 수 없어 **사용자 확인이 아직 남아있다** — 이 부분을 아직
"완료"라고 부르지 않는다.

---

## 1. 1단계 — 노트북 (완료, 더 손댈 것 없음)

- 산출물: `02_notebook/similar_task_search.ipynb`
- 계획 문서: `00_docs/superpowers/plans/2026-08-22-rnd-similar-task-search-plan.md` (Task 1~10, 전부 완료)
- 스펙: `00_docs/superpowers/specs/2026-08-21-rnd-similar-task-search-design.md` (개정 2, 사용자 승인 완료)
- Task 1~10 모두 구현 → 태스크별 리뷰(spec+quality) → **전체 브랜치 최종 리뷰(Opus)**까지 완료.
  최종 리뷰에서 개별 태스크 리뷰로는 못 잡는 통합 결함 4건(마크다운 제목 위치, 위젯 메타데이터에 남은
  연구자 실명, 화면2가 화면1 입력과 안 연결됨, 클러스터 지도 중복 렌더링)을 발견 → 수정 라운드 1회로
  전부 해결 → 재검토까지 클린.
- **완료조건 4개 중 코드/로직으로 검증 가능한 부분은 전부 확인됨.** 단, 실제 브라우저에서 ipywidgets를
  클릭해보는 부분은 에이전트가 할 수 없어서 **사용자가 직접 확인해야 하는 채로 남아있다** — 발표 전에
  `jupyter notebook 02_notebook/similar_task_search.ipynb`을 열어 Restart & Run All 후 완료조건 4개를
  직접 눈으로 확인할 것.
- 이 노트북 파일은 **2단계 작업에서 절대 수정하지 않는다** — 완료된 별도 산출물.
- 최종 커밋: `013b93f`(완료조건 검증+출력정리) → `ddf14c6`(최종 리뷰 수정) 까지. `.superpowers/sdd/` 아래
  이 계획의 작업공간은 다 끝나서 삭제됨(기록은 git 히스토리에 있음).

---

## 2. 2단계 — 웹앱 (진행 중, 여기서 이어서 시작)

### 2.1 계기

사용자가 `00_docs/design-brief.md`(1단계 작업 중 제가 정리해둔 디자인 브리프)를 Claude Design에 넣어
**"UI mockups for design-brief-handoff.zip"**을 받아왔다(프로젝트 루트에 있음, git에 아직 안 올라감).
안에 `RnD 유사과제 검색.dc.html`이 화면1(입력+통계카드+유사과제표+연구자추천표)·화면2(SVD 산점도+범례)
를 정확히 브리프대로 시각화한 목업이었고, 번들의 README가 "코딩 에이전트가 실제 기술스택으로
pixel-perfect 구현"하라고 명시되어 있었다. 이건 스펙에서 "오늘(1단계) 범위 아님"으로 미뤄둔 2단계
작업이라 **사용자에게 직접 물어서 범위 확장을 승인받았다** (2026-08-22):
- 2단계로 지금 넘어간다 (Y)
- 데이터/로직 연결 방식: **가벼운 로직 서버** (정적 JS 전용이 아니라 서버 방식)
- 서버 프레임워크: **FastAPI**

### 2.2 계획 문서 및 현재 진행 상태

계획: `00_docs/superpowers/plans/2026-08-22-rnd-similar-task-search-webapp-plan.md` (Task 1~5)
SDD 워크스페이스/원장: `.superpowers/sdd/2026-08-22-rnd-similar-task-search-webapp-plan/progress.md`
(아직 삭제 안 함 — 계획이 안 끝났으니 다음 세션이 이어서 씀)

| Task | 내용 | 상태 |
|---|---|---|
| 1 | `03_webapp/backend/pipeline.py`(노트북 알고리즘 독립 재구현) + `main.py` FastAPI 스켈레톤 | ✅ 완료, 리뷰 클린 |
| 2 | `/api/clusters`, `/api/search` 엔드포인트 | ✅ 완료, 리뷰 클린 |
| 3 | 프론트엔드 정적 뼈대 (`index.html`, `styles.css`, 목업 시각 재현) | ✅ 완료 |
| 4 | 프론트엔드 JS (`app.js`, API 연동 + 화면1/화면2 렌더링) | ✅ 완료 |
| 5 | 완료조건 검증 + 실행 문서화(`03_webapp/README.md`, HANDOFF/PROJECT_PLAN 갱신) | ✅ 문서화 완료. **단, 완료조건 4개의 브라우저 시각 확인(2.5절)은 사람이 아직 안 함** |

**다음 세션 시작 방법**: 2단계 코드 구현(Task 1~5)은 모두 끝났다. 다음으로 할 일은 새 Task가 아니라
**사람이 `03_webapp/README.md`의 커맨드로 서버를 띄우고 브라우저에서 완료조건 4개를 직접 확인하는
것**(2.5절 참고)이다. 그 확인이 끝나면 이 SDD 워크스페이스(`.superpowers/sdd/2026-08-22-rnd-similar-task-search-webapp-plan/`)와 계획 문서를 정리하고, 커밋되지 않은 파일들(5절 참고)을 사용자와 상의해
정리하면 2단계가 완전히 마무리된다.

### 2.3 Task 1~2 진행 중 발견된 것 (다음 세션이 알아야 할 것)

1. **서버 기동 커맨드가 계획의 예상과 달랐다.** 계획은 "`03_webapp`이 숫자로 시작해서 모듈 경로로 못
   쓸 수 있다"고 걱정했는데 실제로는 문제없었다. 진짜 문제는 Windows 콘솔 코드페이지(cp1252)가 한글
   `print()`에서 `UnicodeEncodeError`를 낸 것 — 실제로 동작하는 커맨드:
   ```powershell
   $env:PYTHONIOENCODING = "utf-8"
   cd C:\project
   C:\project\.venv\Scripts\python.exe -m uvicorn 03_webapp.backend.main:app --port 8000
   ```
   Task 5에서 `03_webapp/README.md` 쓸 때 이 커맨드를 그대로 쓸 것.
2. **계획 자체의 결함 1건을 Task 2에서 찾아서 고쳤다**: `pipeline.py`의 `search_similar_tasks`가 매칭된
   과제 목록을 `"table"` 키로 반환하는데, 아직 안 쓴 Task 4 프론트 JS 코드는 `/api/search` 응답에
   `"tasks"` 키를 기대하도록 계획에 적혀 있었다(계획 작성 시 실수). Task 2 구현자가 `main.py`
   엔드포인트 레벨에서 `table`→`tasks`로 이름을 바꿔 응답해서 해결(`pipeline.py`는 손대지 않음 —
   `recommend_researchers`도 내부적으로 `"table"` 키를 쓰고 있어서 거기까지 건드리면 위험했음).
   **Task 4를 구현할 때 이미 이 문제가 해결된 채로 `/api/search`가 `tasks`/`researchers` 키를 준다는
   것을 전제로 하면 된다** — 계획 문서의 Task 4 코드(`result.tasks`, `result.researchers`)는 그대로 맞다.
3. **클러스터에 의미 라벨을 붙이지 않기로 확정**했다(계획의 Global Constraints에 명시) — 목업은
   "바이오 소재" 같은 지어낸 라벨을 보여주지만, 실제 KMeans 클러스터는 비지도학습 결과라 근거 없는
   라벨을 붙이면 스펙에서 기각한 "기술이전 예측"과 같은 문제(없는 값 발명)가 된다. 프론트는
   "클러스터 0" ~ "클러스터 5"로만 표시.
4. **API 레벨 검증은 전부 끝났다** (curl/Invoke-RestMethod로 실제 호출): `/api/clusters` 1680건/6클러스터,
   예시 3문장 각각 count=30/8/7(모두 >0), 빈 문자열→`blank_query:true`, 한 글자("가")→`reference_only:true`
   (에러 없음), 랭킹 드롭다운 3종×예시 3문장=9회 조합 전부 `researchers=5`·에러 없음. Task 3/4로 실제
   화면(`index.html`/`styles.css`/`app.js`)까지 만들어졌고, **남은 건 사람이 브라우저로 직접 클릭해보는
   것뿐이다** (2.5절 참고).

### 2.4 Task 3~5 진행 중 참고한 것 (완료됨)

- `03_webapp/frontend/fonts/`에 NanumSquare 폰트 4개(L/R/B/EB)가 목업에서 복사되어 Task 3에서 함께
  커밋됨.
- 목업의 `_ds/`(Cal.com 디자인시스템 번들)와 `x-dc`/`sc-for`/`sc-if`/`x-import` 커스텀 태그는 **가져오지
  않고** 순수 HTML/CSS/바닐라 JS로 같은 시각 결과를 재현했다(색상·grid·spacing 구체값은
  `00_docs/superpowers/plans/2026-08-22-rnd-similar-task-search-webapp-plan.md` Task 3/4 섹션 참고).
- Task 5의 완료조건 검증 중 "브라우저 클릭 확인"은 **에이전트가 할 수 없어서 하지 않았다** — API 레벨
  검증(Task 2에서 끝남, 위 4번 항목)까지만 근거로 보고했고, 브라우저 확인은 사람이 할 일로 남겼다.

### 2.5 지금 남은 것 — 사람이 브라우저로 확인할 완료조건 4개

서버 실행 방법은 `03_webapp/README.md` 참고(요약: `$env:PYTHONIOENCODING="utf-8"` 설정 후 `C:\project`에서
`C:\project\.venv\Scripts\python.exe -m uvicorn 03_webapp.backend.main:app --port 8000`, 브라우저에서
http://127.0.0.1:8000/static/index.html). 이 명령은 Task 5에서 실제로 재실행해 200 OK와 정상 응답을
재확인함.

PROJECT_PLAN.md 3절의 완료조건 4개 중 아래는 **API 레벨로는 이미 검증됐지만, 화면에 실제로 그려지는지는
사람이 브라우저로 열어서 봐야 확인된다**:

1. 예시 주제 3문장을 입력창에 입력 → 결과 표에 1건 이상 (API: count=30/8/7로 이미 확인)
2. 화면1 결과 표 한 행의 클러스터 번호와 화면2 지도에서 그 색의 점이 실제로 있는지 대조 (API 레벨
   대조는 안 됨 — 순전히 시각 확인 항목)
3. 입력창을 비우거나 한 글자만 넣고 검색 → 에러 화면 없음 (API: `blank_query:true`/`reference_only:true`,
   HTTP 에러 없음으로 확인. 브라우저 콘솔/렌더링 에러 여부는 미확인)
4. 예시 3개 × 랭킹 드롭다운 3개 = 9회 전환 → 에러 없이 표가 바뀜 (API: 9조합 전부 `researchers=5`·에러
   없음으로 확인. 실제 드롭다운 조작 시 화면 갱신은 미확인)

**이 4가지는 아직 "완료"라고 부르지 않는다.** 다음 세션(또는 사용자 본인)이 위 서버를 띄우고 브라우저로
직접 열어 확인해야 한다.

---

## 3. 확정된 사실 (실제 데이터로 측정한 값 — 1단계 노트북과 2단계 백엔드 모두 이 값으로 재현됨)

데이터 위치: `C:\project\01_data\`, **인코딩 cp949** (utf-8로 열면 깨짐)

| 항목 | 값 |
|---|---|
| 특구입주기업현황.csv | 6,359건 / 고유 기관 6,258개 |
| 이알앤디_과제정보.csv | 11,788건 |
| 보안과제(`보안과제여부 == 'Y'`) 제외 후 | 11,783건 |
| 기관명 조인(양쪽 `.str.strip()`만, 접미사 제거 안 함, 회사측 중복명 dedup 후 병합) | **27개 기관 / 1,680건** |
| 매칭 데이터 내 고유 연구자 | 1,464명 |
| 동명이인(이름 같고 연구자번호 다름) | 64건 |
| 이름+소속기관까지 같은데 다른 사람 (연구자번호 뒷4자리 표기 대상) | **11쌍** |
| 최종 확정 파라미터 | `SIMILARITY_THRESHOLD=0.15`, `N_CLUSTERS=6`, `TOP_N_TASKS=5`, `TOP_N_RESEARCHERS=5` |

**정규화 방식 주의**: 스펙에 한때 "법인 접미사 제거"라고 적혀 있었으나 실측 결과 접미사 제거를 하면
27개/1,680건이 아니라 30개/2,008건으로 어긋난다(매칭된 27개 기관이 전부 대학·출연연·진흥원이라 원래
접미사가 없고, 제거 로직이 무관한 이름을 우연히 겹치게 만듦). **`.str.strip()`만 적용하는 게 맞다** —
스펙 문서도 이 세션에서 이 사실을 반영해 수정해뒀다.

동명이인 표기: 이름+기관이 겹치는 11쌍만 이름 뒤에 연구자번호 뒷 4자리 (`홍길동(1234)` 형태).

---

## 4. 기각된 것과 이유 (다시 논의하지 않으려면 읽을 것)

| 기각된 것 | 이유 |
|---|---|
| **기술이전 성과 발생 예측** | 데이터에 label이 없음. 특허·기술이전·매출 컬럼 전무. `사업년도==선정년도`가 11,788건 전부 일치해 다년도 추적 불가 |
| **기업↔연구자 매칭** (그 명칭) | 조인된 27개 기관 중 실제 기업은 1개뿐. 연구자 추천으로 재정의 |
| **웹앱 클러스터에 의미 라벨 붙이기** (2단계에서 새로 결정) | 비지도학습 결과에 근거 없는 라벨은 위 "기술이전 예측" 기각과 같은 이유로 위험 — "클러스터 N"으로만 표시 |

---

## 5. 파일 현황

```
C:\project\
├── 01_data\                              (cp949 CSV 2개, gitignore로 제외)
├── 02_notebook\
│   └── similar_task_search.ipynb         ← 1단계 완료 산출물 (더 수정 안 함)
├── 03_webapp\
│   ├── backend\
│   │   ├── __init__.py
│   │   ├── pipeline.py                   ← Task 1 완료 (노트북 알고리즘 독립 재구현), 커밋됨
│   │   └── main.py                       ← Task 1~2 완료 (FastAPI, /api/clusters, /api/search), 커밋됨
│   ├── frontend\
│   │   ├── index.html, styles.css        ← Task 3 완료 (목업 시각 재현), 커밋됨
│   │   ├── app.js                        ← Task 4 완료 (API 연동 + 화면1/화면2 렌더링), 커밋됨
│   │   └── fonts\                        ← NanumSquare 4종 (목업에서 복사), 커밋됨
│   └── README.md                         ← Task 5 완료 (실행 방법), 커밋됨
├── 00_docs\
│   ├── design-brief.md                   ← Claude Design에 넣었던 디자인 브리프 (커밋 안 됨)
│   ├── project-plan-report.md            ← 정체 불명 — 이 세션의 2단계 작업 범위 밖에서 생성됨(발표용
│   │                                        계획서로 추정), Task 5에서 손대지 않음. 다음 세션에서 출처 확인 필요
│   ├── superpowers\specs\
│   │   └── 2026-08-21-rnd-similar-task-search-design.md   ← 스펙 개정 2 (정규화 문구 수정됨, 커밋 안 됨)
│   └── superpowers\plans\
│       ├── 2026-08-22-rnd-similar-task-search-plan.md            ← 1단계 계획 (완료, 커밋 안 됨)
│       └── 2026-08-22-rnd-similar-task-search-webapp-plan.md     ← 2단계 계획 (Task 1~5 전부 완료, 커밋 안 됨)
├── .superpowers\sdd\
│   └── 2026-08-22-rnd-similar-task-search-webapp-plan\   ← 2단계 SDD 원장(progress.md). 계획상 Task는 다
│     끝났지만 사람의 브라우저 확인(2.5절)이 남아있어 정리 여부는 보류
├── "UI mockups for design-brief-handoff.zip"   ← 사용자가 올린 Claude Design 핸드오프 번들 (커밋 안 됨,
│                                                  git에 올릴지 결정 안 됨 — 다음 세션에서 물어볼 것)
├── requirements.txt                      ← pandas/scikit-learn/plotly/ipywidgets/notebook/nbformat
│                                             + fastapi/uvicorn 등 (BOM 없음)
├── PROJECT_PLAN.md                       ← 완료조건 4개 유지, 2단계 진행 상태 절 추가(Task 5에서 갱신)
├── DESIGN_LOG.md                         ← 개정 2 반영 완료(연구자 추천, 0건 처리 결정 과정), 커밋 안 됨
└── HANDOFF.md                            ← 이 파일
```

**중요**: `03_webapp/`(backend+frontend+README)는 Task 1~5 진행 중 각 태스크가 끝날 때마다 이미 커밋됐다
(아래 6절 커밋 목록 참고). 반면 `00_docs/superpowers/plans/`, `00_docs/design-brief.md`, 스펙/DESIGN_LOG
수정본, `project-plan-report.md`, zip 파일은 **여전히 커밋 안 됨**(git status 참고) — 다음 세션에서
사용자와 상의해서 정리할 것. Task 5에서 이 파일들을 정리·커밋하지 않은 이유: 이 작업들은 원래 Task 5
범위(`03_webapp/README.md`, `HANDOFF.md`, `PROJECT_PLAN.md`)가 아니고, "사용자가 명시적으로 요청할 때만
커밋" 원칙을 지켰다.

---

## 6. Git / GitHub 현황

- 브랜치 `main`에서 직접 작업 중(사용자가 명시적으로 동의함 — 1일짜리 개인 프로토타입, 별도 브랜치 없음)
- **origin/main보다 17개 이상 커밋 앞서 있고 아직 푸시 안 함** (Task 5 커밋 포함하면 더 늘어남 —
  `git status`로 정확한 수 확인)
- remote = `https://github.com/rome5200/R-D.git` (private)
- 푸시는 인증 창이 필요해 에이전트가 못 함 → 사용자가 직접 `git push` 실행해야 함
- `01_data/*.csv`, `.venv/`, `.omc/`는 `.gitignore`로 계속 제외 — 이 원칙 유지

---

## 7. 환경 정보

- Python 3.13.15 기반 `.venv`(`C:\project\.venv`) — pandas, scikit-learn, plotly, ipywidgets, notebook,
  nbformat, nbconvert, **fastapi, uvicorn**(2단계에서 추가) 전부 설치됨
- Windows Server 2022, 콘솔이 cp1252라 한글 `print()` 시 `UnicodeEncodeError` 남 →
  `$env:PYTHONIOENCODING="utf-8"`을 먼저 설정하고 실행할 것 (특히 uvicorn 서버 기동 시 필수, 위 2.3절
  참고)
- 사용자가 Python 3.11.x를 원했으나 "3.11 설치는 나중에, 지금은 그대로 두자"로 보류 중 (winget·pyenv
  둘 다 이 환경에 없음)

---

## 8. 다음 세션 첫 행동 (그대로 따라 하면 됨)

**2단계 웹앱 계획(Task 1~5)의 코드/문서 구현은 전부 끝났다.** 다음 세션에서 할 새 구현 Task는 없다.
남은 건:

1. 이 파일(특히 2.5절)을 읽고 `git status --short`로 현재 상태가 이 문서와 일치하는지 확인한다
2. **사용자에게 `03_webapp/README.md`의 커맨드로 서버를 띄우고 브라우저에서 완료조건 4개(2.5절, 또는
   `PROJECT_PLAN.md` 3절)를 직접 확인해달라고 요청한다** — 에이전트가 대신 할 수 없는 부분
3. (선택) 1단계 때처럼 2단계 전체에 대한 최종 브랜치 리뷰(Opus)를 돌려서 Task별 리뷰로 못 잡는 통합
   결함이 있는지 확인한다
4. 사용자 확인이 끝나면: `.superpowers/sdd/2026-08-22-rnd-similar-task-search-webapp-plan/`(SDD
   워크스페이스) 정리 여부, 그리고 5절에 남아있는 커밋 안 된 파일들(계획 문서, 디자인 브리프, zip 등)을
   커밋할지/`.gitignore`에 넣을지를 사용자와 상의해서 정리한다
5. `origin/main`에 대한 `git push`는 인증이 필요해 에이전트가 못 한다 — 사용자가 직접 실행해야 한다
