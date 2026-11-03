# 디딤돌 — 정리된 공식 개발 프로젝트

이 ZIP은 현재 Streamlit Community Cloud 배포에 사용되는 `jungeun5264/didimdol1`의
`main` 브랜치, `didimdol_예선/app.py`를 기준으로 정리했습니다.

**현재 기능과 실행 경로를 유지하면서 화면 이모티콘을 제거한 정리본입니다.**
기존 버전인 `capstone` 및 `capstonetest_1`의 코드를 섞지 않았습니다.

## 시작하기
1. `didimdol_예선/` 폴더로 이동합니다.
2. `python -m pip install -r requirements.txt`
3. `python -m streamlit run app.py`
4. 로그인·훈련을 실제 API로 테스트하려면 `didimdol_예선/.streamlit/secrets.toml.example`을 복사해 `secrets.toml`을 만들고 실제 키를 설정합니다. 사용자 기록을 지속 저장하는 배포에는 외부 `DATABASE_URL`도 필요합니다.

## 확인할 문서
- [프로젝트 구조](didimdol_예선/docs/PROJECT_STRUCTURE.md)
- [정리 내용 및 보존 사항](didimdol_예선/docs/CHANGES.md)
- [기존 GitHub·Streamlit에 적용하는 순서](didimdol_예선/docs/DEPLOY_GUIDE.md)
- [앱 사용/개발 안내](didimdol_예선/README.md)

**보안:** 원본 ZIP에 있던 `didimdol_users.sqlite3` 데이터베이스 및 `__pycache__`는 이 ZIP에 포함하지 않았습니다. DB 백업은 원본을 안전한 비공개 장소에 보관하세요. `.gitignore`는 기존에 Git이 추적하던 파일을 자동 삭제하지 않습니다.
