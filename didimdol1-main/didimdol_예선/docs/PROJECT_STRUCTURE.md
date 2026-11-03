# 디딤돌 파일 역할과 연결 관계

## 실행 흐름
```
Streamlit Cloud
  └── didimdol_예선/app.py  (실행 시작 및 화면 이동)
      ├── 홈 / 진단 소개 → friend_pages.py
      │    ├── index.html + style.css
      │    └── diagnosis.html + diagnosis.css
      ├── 로그인 / 회원가입 → auth.py → store.py
      ├── 실제 사전진단 → test.py → auth.py → store.py
      ├── 심화 교육 → training.py
      │    ├── missions.py (상황/과제)
      │    ├── scoring.py (점수 계산)
      │    ├── luna_service.py (AI API)
      │    └── store.py (수행 기록)
      ├── 마이페이지 → mypage.py → store.py
      └── Prompt Coach → app.py 안내 화면(미구현)
```

## 파일 종류

**실행 시작 및 화면**
- `app.py`: 전체 페이지 라우터, 로그인 보호, 스타일 진입점
- `friend_pages.py`: 친구 HTML 원본의 링크를 Streamlit 경로에 연결
- `index.html` / `diagnosis.html`: 소개 페이지(친구 원본, 바이트 단위 보존)
- `style.css` / `diagnosis.css`: 소개 페이지 스타일(친구 원본, 바이트 단위 보존)
- `ui.css` / `training.css` / `mypage.css`: Streamlit 내 페이지별 스타일

**계정 및 기록**
- `auth.py`: 인증, 계정 상태, 사용자 진단 저장 연결
- `store.py`: SQLite 또는 PostgreSQL 저장소
- `mypage.py`: 저장된 사전진단과 훈련 결과 시각화

**AI 학습과 평가**
- `test.py`: 7개 상황 사전진단, 채점, 이전 답변 수정
- `training.py`: 상황 선택·대화·훈련 흐름 및 결과
- `luna_service.py`: OpenAI API 통신, 평가 구조
- `missions.py`: 미션 콘텐츠
- `scoring.py`: 역량별 점수 계산 로직

**실행·참고**
- `requirements.txt`: 라이브러리 목록
- `START_WINDOWS.bat`: Windows 로컬 실행
- `.streamlit/secrets.toml.example`: 안전한 설정 예시(실제 키 없음)
- `FRIEND_ORIGINALS_SHA256.txt`: 친구의 네 원본 파일 해시
- `reference_original/test_original.py`: 사전진단 원본 참고 파일(앱 실행에 미사용)
- `docs/`: 프로젝트 구조, 정리 기록, 배포 가이드

## 건드리기 전에 알아둘 점
1. Streamlit 배포 설정: 저장소 `jungeun5264/didimdol1`, 브랜치 `main`, 실행 경로 `didimdol_예선/app.py`.
2. `index.html` 등 네 원본 파일과 `friend_pages.py`는 함께 작동합니다. 서로의 위치를 무작정 바꾸지 마세요.
3. 사전진단 질문이나 점수 규칙은 `test.py`, 심화 교육 점수는 `scoring.py` / `luna_service.py`에 있으며 서로 다릅니다.
4. `store.py`와 `auth.py`를 변경할 때는 사용자 데이터/진단 세션에 영향을 주는지 확인합니다.
5. `capstone`, `capstonetest_1` 저장소는 작업 이력으로 보관하고, 이 정리본에 중복 복사하지 않습니다.
