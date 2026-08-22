# 2단계 웹앱 실행 방법

## 준비
`.venv`에 fastapi/uvicorn이 설치되어 있어야 한다 (루트의 `requirements.txt` 참고).
`01_data/`에 원본 CSV 2개(cp949 인코딩)가 있어야 한다 — 서버 기동 시 이 파일들을 읽어 메모리에
파이프라인을 구축한다.

## 서버 실행

프로젝트 루트(`C:\project`)를 작업 디렉터리로 두고 다음을 실행한다. Windows 콘솔 코드페이지(cp1252)가
파이프라인 로드 시 찍는 한글 `print()` 출력에서 `UnicodeEncodeError`를 내기 때문에, `PYTHONIOENCODING`을
먼저 `utf-8`로 설정해야 한다.

```powershell
$env:PYTHONIOENCODING = "utf-8"
cd C:\project
C:\project\.venv\Scripts\python.exe -m uvicorn 03_webapp.backend.main:app --port 8000
```

(패키지 이름 `03_webapp`이 숫자로 시작하지만 모듈 경로 실행 자체는 문제없이 동작한다 — 실제로 막히는
지점은 콘솔 인코딩 쪽이었다.)

서버가 뜨면 콘솔에 다음과 같은 로그가 찍힌다:

```
파이프라인 로드 완료: 1680건 / 27개 기관
```

브라우저에서 http://127.0.0.1:8000/static/index.html 접속.

## 데이터

서버 시작 시 `01_data/`의 CSV 2개(특구입주기업현황.csv, 이알앤디_과제정보.csv)를 읽어 보안과제 제외 →
기관명 조인 → TF-IDF/TruncatedSVD/KMeans 학습까지 메모리에서 한 번 수행한다. DB나 외부 저장소는 쓰지
않으며, 서버를 재시작하면 파이프라인을 처음부터 다시 구축한다.

## API

- `GET /api/clusters` — 전체 과제의 SVD 2D 좌표 + 클러스터 번호 (화면2 산점도용)
- `GET /api/search?query=...&rank_by=...` — 입력 주제에 대한 유사 과제/연구자 추천 결과 (화면1용).
  `rank_by`는 `최고 유사도` / `유사 과제 건수` / `합산 점수` 중 하나.

## 알려진 제약

- 클러스터에는 의미 라벨을 붙이지 않는다 ("클러스터 0" ~ "클러스터 5"로만 표시) — 비지도학습 결과에
  근거 없는 라벨을 붙이는 것을 의도적으로 피했다.
