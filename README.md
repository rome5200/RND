# 국가R&D 클러스터 기반 유사과제 조회 서비스

신규 과제를 기획하는 사람이, 준비 중인 주제를 입력하면 **비슷한 기존 과제가 몇 건 있고 어떤 기관이
수행했는지, 중복투자 위험은 어느 정도인지, 특정 특구에 기술이 편중돼 있는지**까지 확인하는 서비스.
1단계는 Jupyter 노트북 프로토타입, 2단계는 이를 FastAPI + 정적 웹 프론트로 확장한 웹앱, 3단계는
화면1 검색에 임베딩을 보강, 이후 A.2/A.3 확장으로 위험도·에고그래프·지역편중 분석까지 추가됐다.

## 현재 상태

**1단계(노트북)·2단계(웹앱)·3단계(임베딩 보강)·A.2/A.3 확장(위험도·에고그래프·지역편중) 모두 구현 완료.**
가장 상세한 이력·현황은 [HANDOFF.md](HANDOFF.md)에 정리되어 있다(특히 §10).

| 산출물 | 상태 |
|---|---|
| 설계 문서 | 완료 (개정 2) |
| 데이터 실측 검증 | 완료 |
| 노트북 구현 (`02_notebook/`) | **완료** (구현+리뷰+최종 통합 리뷰까지 통과) |
| 웹앱 구현 (`03_webapp/`) | **완료** — 화면 4개(검색/클러스터맵/에고그래프/지역편중), FastAPI 백엔드 + 정적 프론트 |
| 화면1 임베딩 보강 (3단계) | **완료** — TF-IDF와 문장 임베딩(`jhgan/ko-sroberta-multitask`) 중 큰 유사도 사용 |
| A.2 위험도 버킷·에고그래프 | **완료** — `/api/search`의 `risk_bucket`, 신규 `/api/ego_graph` |
| A.3 지역 기술편중 | **완료** — 신규 `/api/region`, `/api/clusters`의 클러스터×특구 크로스탭 |
| 패키지 설치 | `requirements.txt` 참고 (fastapi/uvicorn/scikit-learn + sentence-transformers/torch, CPU 전용) |

## 문서

| 파일 | 내용 |
|---|---|
| [HANDOFF.md](HANDOFF.md) | **작업 이어서 하려면 여기부터** — 전체 이력, 확정 사실, 기각된 것, 남은 작업 |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | 화면 구성, 완료 조건, 범위 밖, 아키텍처, 위험과 대안 |
| [DESIGN_LOG.md](DESIGN_LOG.md) | 설계 과정 기록 (주제 좁힌 과정, 방법 선택, 범위 결정) |
| [00_docs/design-brief.md](00_docs/design-brief.md) | 화면 구조/디자인 브리프 |
| [00_docs/api-contract-search.md](00_docs/api-contract-search.md) | `/api/search`·`/api/ego_graph`·`/api/region` 응답 스키마 계약(개발자용) |
| [00_docs/superpowers/specs/](00_docs/superpowers/specs/) | 상세 설계 문서 |
| [01_data/README.md](01_data/README.md) | 원본 데이터 받는 방법 |
| [03_webapp/README.md](03_webapp/README.md) | 웹앱 실행 방법 |

## 기능 (설계 기준)

**섹션 01 — 유사 과제 검색 (핵심)**
- 주제를 입력하면 TF-IDF·문장 임베딩 결합 유사도로 유사 과제를 검색
- 유사 과제 건수 / 수행 기관 목록 / 과제 Top-N 표 / 클러스터 번호 / 위험도 배지(높음·중간·낮음, 규칙 기반) 출력
- **연구자 추천 표** — 내 주제와 비슷한 과제를 수행한 연구자 (랭킹 기준 드롭다운으로 전환)
- 인라인 특구집계 바 — 유사 과제 중 특구소속 비율 + Top-3

**섹션 02 — 전체 클러스터 지도 (보조)**
- TruncatedSVD 2D + KMeans 클러스터 산점도, 입력 주제 위치를 하이라이트
- 클러스터×특구 크로스탭 히트맵

**섹션 03 — 유사 과제 관계망 (에고 그래프)**
- 질의·유사 과제 Top-N·연구책임자·세부사업을 노드/엣지로 시각화, 소수 수행 사업유형은 점선으로 표시

**섹션 04 — 지역 기술편중 분석**
- 전체 코퍼스(11,783건) 대비 특구소속 비율, 특구별 분포, 편중지표(LQ)

## 구조

```
02_notebook/   1단계 — Jupyter 노트북 프로토타입 (완료 산출물, 더 수정 안 함)
03_webapp/     2단계~ — FastAPI 백엔드 + 정적 프론트 웹앱 (실행 방법: 03_webapp/README.md)
01_data/       원본 CSV (gitignore로 제외, 받는 방법은 01_data/README.md)
```

## 데이터

공공데이터포털 CSV 2종 (수동 다운로드). **개인정보 포함으로 저장소에 커밋하지 않음** —
[01_data/README.md](01_data/README.md) 참고.

런타임 중 외부 API·네트워크 호출은 없다. DB는 사용하지 않는다 — FastAPI가 서버 시작 시 CSV를
메모리에 올려 파이프라인을 한 번 구축하는 가벼운 로직 서버다.

## 실행

```bash
# 1. 01_data/README.md 를 보고 CSV 2개를 01_data/ 에 넣는다
# 2. 패키지 설치
pip install -r requirements.txt   # pandas/scikit-learn + fastapi/uvicorn + sentence-transformers/torch(CPU)

# 3. 설계 문서를 Word 파일로 내보내려면
python make_docx.py    # PROJECT_PLAN.md + DESIGN_LOG.md → PROJECT_DESIGN.docx

# 4. 웹앱을 실행하려면 03_webapp/README.md 참고 (서버 기동 커맨드·인코딩 주의사항 포함)
```

`make_docx.py`의 `PROJECT_TITLE` 변수에 문서 제목을 직접 적어야 한다 (현재 플레이스홀더).

## 환경 메모

- CSV 인코딩은 **cp949**
- Windows 콘솔이 cp1252라 한글 `print` 시 `UnicodeEncodeError` — 서버 기동 전 `PYTHONIOENCODING=utf-8` 설정 필요
- Windows에서 `torch` 실행에는 Microsoft Visual C++ 재배포 패키지(`vc_redist.x64.exe`)가 필요 (없으면 `import torch`가 `c10.dll` 오류)
- 임베딩 모델(`jhgan/ko-sroberta-multitask`, 약 400MB)은 최초 실행 시 1회만 인터넷에서 다운로드되고 이후 로컬 캐시만 사용 — 자세한 내용은 `03_webapp/README.md` 참고
