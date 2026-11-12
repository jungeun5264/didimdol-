# 디딤돌 프론트엔드 통합 패치 — 적용 방법

## 무엇을 수정하나요?
친구가 전달한 HTML·CSS·이미지 9개를 기존 Streamlit `home` / `diagnosis` 소개 페이지에 적용합니다.
`app.py`, `auth.py`, `test.py`, `training.py`, `store.py`, `community.py`, `mypage.py`, `ui.css`는 수정하지 않습니다.

## 파일 배치
`app.py`와 같은 폴더에 아래 파일이 있어야 합니다.

```
app.py                     (기존 그대로)
friend_pages.py            (이 ZIP 파일로 교체)
index.html                 (이 ZIP 파일로 교체)
diagnosis.html             (이 ZIP 파일로 교체)
style.css                  (이 ZIP 파일로 교체)
diagnosis.css              (이 ZIP 파일로 교체)
images/
    card1.png
    card2.png
    card3.png
    card4.png
    question.png
    step1.png
    step2.png
    step3.png
    step4.png
```

현재 새 GitHub 저장소에 `app.py`가 `didimdol_예선/` 안에 있다면 모든 파일을 해당 폴더에 올려주세요. 그 외 기존 폴더 구조와 Streamlit의 Main file path는 변경하지 않습니다.

## GitHub 웹에서 업로드하기
1. 지금 운영 중인 GitHub `didimdol-` 저장소에서 `app.py`가 있는 폴더를 엽니다.
2. 작업 전 백업 브랜치를 만듭니다.
3. `Add file` → `Upload files`로 이 ZIP의 `friend_pages.py`, HTML 2개, CSS 2개(총 5개)를 업로드합니다.
4. `images` 폴더를 업로드할 수 있으면 폴더 전체를 드래그합니다. 업로드 목록에 `images/card1.png`와 같은 경로가 표시되는지 확인합니다.
5. 폴더 업로드가 안 되면 GitHub에서 `Add file` → `Create new file`을 누르고 파일명을 `images/.gitkeep`으로 입력해 먼저 폴더를 만든 뒤, 해당 폴더에 들어가 이미지 9개를 업로드합니다.
6. 변경 사항을 저장하고, 새 Streamlit 앱의 홈·사전진단·메뉴를 확인합니다.

**ZIP 파일 자체를 저장소에 업로드하는 것이 아니라, 압축을 푼 내부 파일을 올리는 것입니다.**

## 연결된 버튼
- 로고와 홈 → `home`
- 사전진단 → `diagnosis`
- 진단 시작하기 → `diagnosis-live`
- 맞춤형 심화 교육 → `training`
- 커뮤니티 → `community`
- 마이페이지 → `mypage`
- 회원가입하기 → `signup`

`app.py`의 기존 `hidden_route_buttons()`와 `st.html(original_fragment(name), unsafe_allow_javascript=True)`가 유지되어 있어야 합니다.

## 수정한 텍스트
- 오래된 '12문항 / 영역별 4문항' 사전진단 안내를 '7개 상황 / 6개 AI 역량'으로 교체했습니다. 회원가입 때 진행하는 Q26 12문항 설문과 혼동하지 않기 위해서입니다.
- 제거하기로 한 Prompt Coach 홍보 문구를 'Luna와 함께하는 실전 AI 코칭'으로 교체했습니다. 별도의 Prompt Coach 메뉴는 새 HTML에 없습니다.
- 모바일에서 메뉴가 사라지지 않도록 가로 스크롤 메뉴를 표시하도록 CSS만 보완했습니다.

## 주의
- 이 ZIP은 홈·사전진단 **소개 페이지** 디자인 교체용입니다. 사전진단 문제 진행, 로그인, 유형 분석 결과, 커뮤니티 화면 디자인은 변경하지 않습니다.
- 원본 CSS는 1440px 데스크톱 기준의 고정 높이/긴 스크롤을 포함합니다. 모니터 크기에 따라 여백이 크게 느껴질 수 있으니 실제 디스플레이에서 점검하세요.
- HTML 브리지는 이미지 파일을 페이지에 직접 삽입하므로 `images/` 폴더가 필수이며 별도의 Streamlit 정적 파일 서비스 설정은 필요하지 않습니다.
- GitHub의 최신 `friend_pages.py`에 다른 개발자가 변경한 기능이 있다면 해당 변경과 병합한 뒤 적용해야 합니다.
- 이 패치는 Python 함수/컴파일 및 HTML 연동 수준의 사전 확인만 거쳤으며, 실제 Streamlit 클라우드에서의 클릭 테스트는 사용자가 확인해야 합니다.
