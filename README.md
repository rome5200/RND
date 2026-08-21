# 국가R&D 클러스터 기반 유사과제 조회 서비스

신규 과제를 기획하는 사람이, 준비 중인 주제를 입력하면 **비슷한 기존 과제가 몇 건 있고 어떤 기관이
수행했는지** 바로 확인하는 Jupyter 노트북 프로토타입 (1단계).

## 현재 상태

**설계 완료 / 구현 미착수** — 이 저장소에는 아직 노트북 구현 코드가 없다.
진행 상황과 다음 할 일은 [HANDOFF.md](HANDOFF.md)에 정리되어 있다.

| 산출물 | 상태 |
|---|---|
| 설계 문서 | 완료 (개정 2, 사용자 검토 대기) |
| 데이터 실측 검증 | 완료 |
| 노트북 구현 | **미착수** |
| 패키지 설치 | 미완 (`scikit-learn`, `plotly`, `ipywidgets`, `notebook` 없음) |

## 문서

| 파일 | 내용 |
|---|---|
| [HANDOFF.md](HANDOFF.md) | **작업 이어서 하려면 여기부터** — 중단 지점, 남은 작업, 미해결 질문 |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | 화면 구성, 완료 조건, 범위 밖, 아키텍처, 위험과 대안 |
| [DESIGN_LOG.md](DESIGN_LOG.md) | 설계 과정 기록 (주제 좁힌 과정, 방법 선택, 범위 결정) |
| [00_docs/superpowers/specs/](00_docs/superpowers/specs/) | 상세 설계 문서 |
| [01_data/README.md](01_data/README.md) | 원본 데이터 받는 방법 |

## 기능 (설계 기준)

**화면 1 — 유사 과제 검색 (핵심)**
- 주제를 입력하면 TF-IDF 코사인 유사도로 유사 과제를 검색
- 유사 과제 건수 / 수행 기관 목록 / 과제 Top-N 표 / 클러스터 번호 출력
- **연구자 추천 표** — 내 주제와 비슷한 과제를 수행한 연구자 (랭킹 기준 드롭다운으로 전환)

**화면 2 — 전체 지도 (보조)**
- TruncatedSVD 2D + KMeans 클러스터 산점도, 입력 주제 위치를 하이라이트

## 데이터

공공데이터포털 CSV 2종 (수동 다운로드). **개인정보 포함으로 저장소에 커밋하지 않음** —
[01_data/README.md](01_data/README.md) 참고.

런타임 중 외부 API·네트워크 호출은 없다. 서버/DB도 사용하지 않는다.

## 실행

```bash
# 1. 01_data/README.md 를 보고 CSV 2개를 01_data/ 에 넣는다
# 2. 패키지 설치 (아직 설치 방식 미결정 — HANDOFF.md 7절 참고)
pip install pandas scikit-learn plotly ipywidgets notebook

# 3. 설계 문서를 Word 파일로 내보내려면
python make_docx.py    # PROJECT_PLAN.md + DESIGN_LOG.md → PROJECT_DESIGN.docx
```

`make_docx.py`의 `PROJECT_TITLE` 변수에 문서 제목을 직접 적어야 한다 (현재 플레이스홀더).

## 환경 메모

- Python 3.13.15에서 확인 (3.11 전환은 보류 상태)
- CSV 인코딩은 **cp949**
- Windows 콘솔이 cp1252라 한글 `print` 시 `sys.stdout.reconfigure(encoding="utf-8")` 필요
