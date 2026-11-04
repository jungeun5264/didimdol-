"""친구 HTML/CSS 파일은 읽기만 합니다. 파일 자체는 절대 수정하지 않습니다.

렌더링된 페이지의 링크를 Streamlit 내부 버튼으로 연결하는 JS 브리지만 추가합니다.
(요구 Streamlit >= 1.52 / st.html unsafe_allow_javascript=True)
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
ROUTES = ('home', 'diagnosis', 'diagnosis-live', 'training', 'mypage', 'login', 'signup', 'community')


def original_fragment(name: str) -> str:
    if name not in ('index.html', 'diagnosis.html'):
        raise ValueError('허용되지 않은 페이지입니다.')
    raw = (ROOT/name).read_text(encoding='utf-8')
    match = re.search(r'<body[^>]*>(.*?)</body>', raw, flags=re.I | re.S)
    if not match:
        raise ValueError('body 요소가 없습니다.')
    body = match.group(1)

    for path, target in (('index.html', 'home'), ('diagnosis.html', 'diagnosis')):
        body = body.replace(
            f'href="{path}"',
            f'href="?view={target}" data-didimdol-route="{target}" target="_self"'
        )
    for label, route in (('맞춤형 심화 교육', 'training'), ('마이페이지', 'mypage')):
        body = body.replace(
            f'<a href="#">{label}</a>',
            f'<a href="?view={route}" data-didimdol-route="{route}" target="_self">{label}</a>'
        )

    body = body.replace('<a href="#">Prompt Coach</a>', '')
    body = body.replace(
        '</nav>',
        '<a href="?view=community" data-didimdol-route="community" target="_self">커뮤니티</a></nav>',
        1,
    )
    body = body.replace(
        '<a href="#" class="btn-white">회원가입하기</a>',
        '<a href="?view=login" data-didimdol-route="login" target="_self" class="btn-white">회원가입하기</a>'
    )
    body = body.replace(
        '<a href="#" class="btn-start">',
        '<a href="?view=diagnosis-live" data-didimdol-route="diagnosis-live" target="_self" class="btn-start">'
    )
    body = body.replace('Prompt Coach<br>를 통한 실시간 코칭', '실시간 AI 활용 코칭')
    body = body.replace(
        'AI 사용법 미숙과 질문 작성의 어려움을 해소할 수 있도록, 목적과 맥락에 맞는 질문법을 실시간으로 교정해 주는 Prompt Coach를 제공합니다.',
        'AI 사용법 미숙과 질문 작성의 어려움을 해소할 수 있도록, 목적과 맥락에 맞는 AI 활용 전략과 질문 방식을 실시간으로 코칭합니다.'
    )

    if name == 'diagnosis.html':
        body = body.replace('소요 시간: 약 3~5분 (총 12문항 / 영역별 4문항)',
                            '소요 시간: 약 5~8분 (총 7개 상황 / 6개 역량)')
        body = body.replace('진단 완료 시 개인별 맞춤 추천 코스와<br>Prompt Coach 실습이 즉시 활성화됩니다.',
                            '진단 완료 시 6개 역량 분석과<br>실전 훈련으로 이동할 수 있습니다.')
    css = (ROOT/'style.css').read_text(encoding='utf-8')
    if name == 'diagnosis.html':
        css += '\n' + (ROOT/'diagnosis.css').read_text(encoding='utf-8')
    shim = '''
    [data-testid="stMainBlockContainer"],.block-container{max-width:100%!important;width:100%!important;padding:0!important;}
    [data-testid="stAppViewContainer"],.stApp{background:#fff!important;}
    [data-testid="stHeader"]{display:none!important;}
    [data-testid="stToolbar"]{display:none!important;}
    #MainMenu,footer{visibility:hidden!important;}
    [data-testid="stVerticalBlock"]{gap:0!important;}
    [data-testid="stElementContainer"]{width:100%;}
    '''
    js = '''<script>
    if (!window.__didimdolRouteListener) {
      window.__didimdolRouteListener = true;
      document.addEventListener('click', function(e) {
        const link = e.target.closest('a[data-didimdol-route]');
        if (!link) return;
        const route = link.getAttribute('data-didimdol-route');
        if (!ROUTES.includes(route)) return;
        const button = document.querySelector('.st-key-route_' + route + ' button');
        if (button) { e.preventDefault(); e.stopPropagation(); button.click(); }
      }, true);
    }
    </script>'''.replace('ROUTES', str(list(ROUTES)).replace("'", '"'))
    return ('<style>@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");\n' +
            css + '\n' + shim + '</style>\n<div class="didimdol-original">' + body + '</div>' + js)
