# 디딤돌 v10 — 회원가입 · 로그인 · 사용자별 진단/훈련 기록

## 주요 특징
- **친구의 원본 파일 네 개 절대 수정 없음**: `index.html`, `diagnosis.html`, `style.css`, `diagnosis.css`. `FRIEND_ORIGINALS_SHA256.txt`에 원본 SHA-256 기록.
- `test.py`: 사용자가 보낸 `test (1).py`의 7개 상황, 6개 역량 × 2점 채점, 답변 수정 기능 보존.
- `training.py`: 사용자가 보낸 최신 `app (8).py` 기반 GPT Luna 전용 훈련과 육각형 결과.
- `auth.py`: 회원가입·로그인·로그아웃, `hashlib.pbkdf2_hmac`으로 비밀번호 해싱.
- `store.py`: 계정/진단/훈련 기록을 사용자별 분리해 저장. SQLite(로컬) 또는 PostgreSQL(공유 배포).
- `app.py`: 통합 진입점. `friend_pages.py`는 **렌더된 HTML 내부에서만** 링크를 내부 Streamlit 버튼에 연결함.
- 로그인/사전진단/훈련은 한 브라우저 탭에서 이동합니다. HTML 링크 JS 연결에 Streamlit **1.52 이상**이 필요합니다.

## Windows에서 실행
1. 이 ZIP을 새 폴더에 압축 해제합니다. `app.py`, `requirements.txt`가 나란히 있는지 확인하세요.
2. 기존 Streamlit 서버가 실행 중이면 터미널에서 `Ctrl+C`로 종료합니다.
3. `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사해 API 키를 입력합니다.
4. `START_WINDOWS.bat`을 더블 클릭하거나 VS Code에서 아래 두 줄을 순서대로 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

5. `http://localhost:8501`에서 회원가입·로그인·사전진단·훈련을 시험합니다.

## 사용 흐름
- 홈페이지에 표시된 **회원가입하기** → 새 계정 등록(로그인까지 자동 진행) → 마이페이지.
- 상단 **마이페이지** → 로그인이 필요한 경우 로그인 페이지가 열립니다.
- 홈/사전진단 안내는 로그인 없이 볼 수 있습니다. 실제 진단 및 훈련은 로그인 필요.
- 진단을 완료하면 점수/답변이 해당 계정 DB에 저장됩니다.
- 훈련이 끝나면 수행 기록과 육각형 프로필이 저장됩니다.
- 로그아웃 후 다른 계정으로 로그인하면 **그 계정의 기록만** 보입니다.
- 저장된 사전진단 결과가 6개 100점 축으로 환산돼 훈련의 회색 육각형에 반영됩니다.

## 주의: Streamlit Cloud에서는 외부 DB가 필수
- 로컬 실행은 프로젝트 폴더에 `didimdol_users.sqlite3`를 자동 생성합니다. 앱 재실행 후에도 로컬 파일이 보존됩니다.
- **Streamlit Community Cloud의 로컬 파일 시스템은 영구 DB로 사용할 수 없습니다.** 앱 재시작/재배포 시 유저 계정과 결과가 없어질 수 있습니다.
- 여러 명이 배포 웹에 가입하고 장기간 기록을 보존하려면 **PostgreSQL**(예: Supabase / Neon)을 먼저 준비해야 합니다.
- 외부 PostgreSQL에서 연결 URL(`postgresql://...`)을 받아 Streamlit Cloud의 `App settings → Secrets`에 아래 값을 입력하세요. DB 테이블은 시작 시 자동 생성됩니다.

```toml
OPENAI_API_KEY = "실제_키"
OPENAI_MODEL = "gpt-6-luna"
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
```

- 로컬에서도 PostgreSQL을 사용하려면 같은 설정을 `.streamlit/secrets.toml`에 입력하면 됩니다.
- 서버가 DB에 접근할 수 있어야 하며, SSL이 지원되어야 합니다.
- DB URL / API 키 / 실제 DB 파일은 GitHub에 업로드하면 안 됩니다. `.gitignore`에 등록되어 있습니다.

## 설계상의 범위와 한계
- 등록한 아이디/비밀번호를 이용하는 **캡스톤 프로토타입용 인증**입니다. 이메일 검증, 비밀번호 재설정, CAPTCHA, 관리자 계정은 아직 구현하지 않았습니다.
- Streamlit 연결이 새로 생성되거나 브라우저를 새로고침하면 **다시 로그인**해야 할 수 있습니다. 그러나 외부 DB 또는 로컬 DB의 기록은 유지됩니다.
- 로그인 시도 제한은 개별 세션당 60초에 5회로 설정되어 있습니다. 불특정 대중에게 공개하는 상용 서비스에는 서버 전체 차원의 속도 제한, 계정 복구, 감사 로그, 데이터 보관 정책 등의 추가 보안이 필요합니다.
- 프로젝트가 이미 사용하고 있던 `OPENAI_MODEL=gpt-6-luna` 설정을 변경하지 않았습니다. 실제 API 계정에서 해당 모델 접근 권한이 없으면 모델 ID/계정 권한을 확인해야 합니다.
- 안내문 내 가상 사례와 사용자 답변이 DB에 저장될 수 있으므로 실제 개인정보 입력을 최소화하고 공개 운영 전에 개인정보 처리방침을 마련하세요.
- 본 환경에서는 Streamlit 브라우저와 OpenAI 실제 API 호출까지 실행하지 못했습니다. Python 구문 검사, 사용자/진단/훈련 DB 분리, 비밀번호 검증, HTML 원본 파일 SHA-256을 확인했습니다.
