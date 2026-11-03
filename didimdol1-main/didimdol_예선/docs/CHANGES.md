# 정리본 변경 내역

## 기존 기능 유지
- `app.py` 라우팅, HTML 링크 연결, 인증, 데이터베이스 접근, 진단 로직, 질문, 평가 기준, 심화 교육과 결과 저장 기능 유지
- 프론트엔드 원본 네 파일(`index.html`, `diagnosis.html`, `style.css`, `diagnosis.css`)의 내용과 SHA-256 유지
- `didimdol_예선/app.py` 실행 경로 유지

## 소스 코드에서 변경한 부분(정확히 2파일)
- `app.py`: Streamlit 앱 탭과 상단 메뉴의 `🌱` 이모티콘 제거
- `test.py`: 단독 실행 모드의 `🤖` 앱 아이콘 제거
- 이외 `.py`, `.html`, `.css` 파일은 내용 변경 없음

## 구성에서 정리한 부분
- Python이 자동 생성하는 `__pycache__/` 및 `*.pyc` 제외
- 실제 사용자 정보를 담은 `didimdol_users.sqlite3` 제외 (기존 원본 ZIP 및 비공개 DB는 별도로 백업)
- `.gitignore` 추가: DB, 자격 증명, 캐시 파일의 새 커밋 방지
- 비밀정보가 없는 `.streamlit/secrets.toml.example` 추가
- 문서 `docs/` 정리 및 기존 상세 README를 `docs/ORIGINAL_README_v10.md`로 보존
- 프로젝트 최상단 README와 앱 폴더 README를 현재 배포 구조에 맞게 개선

## 주의
- `.gitignore`는 **이미 원격 Git에 올라간 DB/키를 제거하지 않습니다.** 기존 추적 해제 및 필요 시 Git 이력 정리가 별도로 필요합니다.
- 이 ZIP에는 기존 계정 데이터가 담겨 있지 않습니다. 기존 DB 내용이 필요한 경우 비공개로 별도 이전해야 합니다.
- Prompt Coach 단독 서비스는 원래부터 미구현 상태이며 임의로 새 기능을 만들지 않았습니다.
- 실제 AI API/외부 DB 연동 및 브라우저 시연까지 확인한 정식 배포 보증은 아닙니다.
