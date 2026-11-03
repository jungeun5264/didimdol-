# GitHub와 Streamlit 배포에 안전하게 반영하기

## 1. 현재 코드 백업
- GitHub의 `jungeun5264/didimdol1`에서 기존 코드를 ZIP으로 한 번 더 저장합니다.
- 가능하면 `main`에서 새 브랜치 `cleanup-no-emoji`를 만들고 이 브랜치에서 먼저 적용합니다.

## 2. 정리본 적용
- 이 ZIP의 `didimdol_예선/` 내부 파일을 기존 GitHub 저장소의 **같은 경로**에 적용하세요.
- `didimdol_예선/app.py` 경로를 변경하지 마세요.
- 추가할 항목: 루트 `README.md`, `.gitignore`, 앱의 `docs/`, `.streamlit/secrets.toml.example`.
- `didimdol_users.sqlite3`, `__pycache__/`는 배포 대상으로 사용하지 마세요.

## 3. 이미 GitHub에 올라간 사용자 DB 주의
- `.gitignore`를 추가해도 **과거에 커밋한 SQLite 파일은 계속 추적됩니다.** 저장소가 공개라면 사용자 기록·비밀번호 해시가 노출되었을 수 있습니다.
- 파일 추적 제거 예시 (실제 저장소에서 실행):
  `git rm --cached "didimdol_예선/didimdol_users.sqlite3"`
- 그리고 새 커밋을 생성해야 합니다. 이미 공개된 과거 이력까지 지워야 한다면 Git 이력 재작성과 협업자 조율이 필요합니다. 실사용 비밀번호를 재사용했다면 비밀번호 변경도 필요합니다.
- 사용 중인 실제 DB를 보존해야 한다면 기존 원본을 **비공개로 백업**하세요. 이 정리본은 백업 DB를 포함하지 않습니다.

## 4. 배포 경로 확인
Streamlit Community Cloud 관리 페이지의 앱 설정에서 아래를 유지합니다.
- Repository: `jungeun5264/didimdol1`
- Branch: `main` (테스트 브랜치로 배포했다면 그 브랜치)
- Main file path: `didimdol_예선/app.py`

## 5. 테스트 체크리스트
- [ ] 홈 화면 로드, 상단 이동 링크
- [ ] 로그인 / 회원가입 / 로그아웃
- [ ] 비로그인 상태에서 진단 실행 또는 훈련 접근 시 로그인으로 이동
- [ ] 사전진단 7개 상황 응답·이전 답변 수정·점수 표시
- [ ] 진단 완료 후 마이페이지 기록 저장
- [ ] 심화 교육 시나리오·API 요청·결과 그래프
- [ ] 로그아웃 후 다른 계정으로 로그인 시 기록 분리
- [ ] PC/모바일에서 글자가 보이는지 확인

## 6. Luna에 전달할 한 줄
> 지금의 `didimdol_예선/app.py` 배포 구조와 진단·인증·저장 코드는 유지하고, 정리본의 파일/문서만 반영해 주세요. 비밀키나 SQLite 파일은 커밋하지 말아 주세요.
