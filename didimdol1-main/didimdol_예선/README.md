# 디딤돌 — 실행 및 기능 안내

이 폴더는 **현재 배포 메인 파일인 `app.py`가 있는 위치**입니다.
로그인, 사전진단, 교육, 결과 저장 기능을 기존대로 유지합니다.

## 실행
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Windows에서는 `START_WINDOWS.bat`도 사용할 수 있습니다.

## 설정
- 로컬 API 설정: `.streamlit/secrets.toml.example`를 `.streamlit/secrets.toml`로 복사한 뒤 실제 API 키와 계정에서 사용 가능한 모델명을 입력합니다.
- 클라우드 설정: Streamlit Cloud → 앱 Settings → Secrets에서 `OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`을 설정합니다.
- **PostgreSQL DATABASE_URL**: 여러 사람이 사용하는 클라우드 서비스에서는 지속되는 사용자 기록을 위해 권장됩니다. 코드에 없으면 SQLite를 사용하며, 클라우드의 로컬 SQLite 파일은 재배포 시 사라질 수 있습니다.
- 이 정리본에는 사용자 정보가 든 `didimdol_users.sqlite3`가 없습니다. 앱을 로컬 실행하면 빈 DB가 자동으로 만들어집니다.

## 페이지
| 메뉴 | 동작 | 주요 파일 |
| --- | --- | --- |
| 홈 | 서비스 소개 | `index.html`, `style.css`, `friend_pages.py` |
| 사전진단 소개 | 안내 및 진단 시작 | `diagnosis.html`, `diagnosis.css`, `friend_pages.py` |
| 로그인/회원가입 | 계정 관리 | `auth.py`, `store.py` |
| 실전 사전진단 | 7개 상황, 6개 역량 채점, 답변 수정 | `test.py` |
| 맞춤형 심화 교육 | AI 기반 훈련, 점수 그래프 | `training.py`, `luna_service.py`, `missions.py`, `scoring.py` |
| 마이페이지 | 내 기록 조회 | `mypage.py`, `mypage.css`, `store.py` |
| Prompt Coach | 현재 안내문만 있음 | `app.py` |

## 변경 원칙
`app.py`의 `view` 라우팅과 HTML 원본의 상대 경로에 의존하므로 배포 안정성을 위해 실행 파일은 같은 폴더에 유지합니다.
친구의 원본 네 파일은 변경하지 않았으며 `FRIEND_ORIGINALS_SHA256.txt`로 비교할 수 있습니다.
상세한 설명은 `docs/` 폴더에 있습니다.
