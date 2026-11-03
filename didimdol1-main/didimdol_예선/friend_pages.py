"""친구 HTML/CSS 파일은 읽기만 합니다. 파일 자체는 절대 수정하지 않습니다.

렌더링된 페이지의 링크를 Streamlit 내부 버튼으로 연결하는 JS 브리지만 추가합니다.
(요구 Streamlit >= 1.52 / st.html unsafe_allow_javascript=True)
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
ROUTES = ('home','diagnosis','diagnosis-live','training','prompt-info','mypage','login','signup')


def original_fragment(name: str) -> str:
    if name not in ('index.html', 'diagnosis.html'):
        raise ValueError('허용되지 않은 페이지입니다.')
    raw = (ROOT/name).read_text(encoding='utf-8')
    match = re.search(r'<body[^>]*>(.*?)</body>', raw, flags=re.I | re.S)
    if not match:
        raise ValueError('body 요소가 없습니다.')
    body = match.group(1)
    # 화면에 보여주는 HTML에서만 링크 연결. 원본 4개 파일 바이트 불변.
    for path, target in (('index.html','home'),('diagnosis.html','diagnosis')):
        body = body.replace(f'href="{path}"',
                            f'href="?view={target}" data-didimdol-route="{target}" target="_self"')
    for label, route in (('맞춤형 심화 교육','training'),('Prompt Coach','prompt-info'),('마이페이지','mypage')):
        body = body.replace(f'<a href="#">{label}</a>',
                            f'<a href="?view={route}" data-didimdol-route="{route}" target="_self">{label}</a>')
    body = body.replace('<a href="#" class="btn-white">회원가입하기</a>',
                        '<a href="?view=login" data-didimdol-route="login" target="_self" class="btn-white">회원가입하기</a>')
    body = body.replace('<a href="#" class="btn-start">',
                        '<a href="?view=diagnosis-live" data-didimdol-route="diagnosis-live" target="_self" class="btn-start">')
    # 안내 텍스트는 표시할 때만 실제 test.py의 7개 상황에 맞춤
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
    #MainMenu,footer{visibility:hidden!important;}
    [data-testid="stVerticalBlock"]{gap:0!important;}
    [data-testid="stElementContainer"]{width:100%;}
    '''
    # Static trusted JS: 클릭을 Streamlit 버튼 이벤트로 전달해 새 페이지 로드 없이 이동
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
        // 버튼이 없으면 href가 백업 경로 역할을 합니다.
      }, true);
    }
    </script>'''.replace('ROUTES', str(list(ROUTES)).replace("'", '"'))
    return ('<style>@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");\n' +
            css + '\n' + shim + '</style>\n<div class="didimdol-original">' + body + '</div>' + js)
