"""디자인 원본 HTML/CSS(index.html·diagnosis.html·login.html 등)는 읽기만 합니다.

파일 자체는 수정하지 않고, 화면에 그릴 때만 아래 세 가지를 덧붙입니다.
  1) 링크 → Streamlit 내부 이동 버튼 연결 (새로고침 없이 이동해 로그인 세션 유지)
  2) images/*.png → data URI 로 인라인 (Streamlit은 상대경로 이미지를 서빙하지 않음)
  3) 로그인 폼 제출 → 숨은 Streamlit 폼으로 전달 (실제 계정 인증)
(요구 Streamlit >= 1.52 / st.html unsafe_allow_javascript=True)
"""
from __future__ import annotations

import base64
import json
import re
from urllib.parse import quote
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROUTES = ('home', 'diagnosis', 'diagnosis-live', 'training', 'community', 'mypage', 'login', 'signup', 'onboarding')
PRETENDARD = '@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");'

# 원본 HTML의 링크 → 내부 경로
_LINKS = (
    ('href="index.html"', 'home'),
    ('href="diagnosis.html"', 'diagnosis'),
    ('href="login.html#signup"', 'signup'),
    ('href="login.html"', 'mypage'),   # 마이페이지: 로그인 안 했으면 로그인 화면으로 이동
)
_HASH_LINKS = (
    ('<a href="#">맞춤형 심화 교육</a>', 'training'),
    ('<a href="#">커뮤니티</a>', 'community'),
    ('<a href="#" class="btn-start">', 'diagnosis-live'),
)

# Streamlit 기본 여백·헤더를 숨겨 원본 페이지가 화면 전체를 쓰게 함
_PAGE_SHIM = '''
[data-testid="stMainBlockContainer"],.block-container{max-width:100%!important;width:100%!important;padding:0!important;}
[data-testid="stAppViewContainer"],.stApp{background:#fff!important;}
[data-testid="stHeader"]{display:none!important;}
#MainMenu,footer{visibility:hidden!important;}
[data-testid="stVerticalBlock"]{gap:0!important;}
[data-testid="stElementContainer"]{width:100%;}
.didimdol-original{line-height:normal;color:#000;}   /* 브라우저 기본값으로 되돌려 원본과 같은 줄 높이 */
.didimdol-original > .header{position:sticky;top:0;z-index:1000;}   /* 스크롤해도 헤더 고정 */
'''

# 링크 클릭을 숨은 Streamlit 버튼 클릭으로 전달 (정적·신뢰 JS)
_ROUTER_JS = '''<script>
if (!window.__didimdolRouteListener) {
  window.__didimdolRouteListener = true;
  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[data-didimdol-route]');
    if (!link) return;
    var route = link.getAttribute('data-didimdol-route');
    if (ROUTES.indexOf(route) < 0) return;
    var button = document.querySelector('.st-key-route_' + route + ' button');
    if (button) { e.preventDefault(); e.stopPropagation(); button.click(); }
    // 버튼이 없으면 href(?view=...)가 백업 경로 역할을 합니다.
  }, true);
}
</script>'''.replace('ROUTES', json.dumps(list(ROUTES)))


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding='utf-8')


def _body(name: str) -> str:
    match = re.search(r'<body[^>]*>(.*?)</body>', _read(name), flags=re.I | re.S)
    if not match:
        raise ValueError(f'{name}: body 요소가 없습니다.')
    return match.group(1)


def _route_attr(route: str) -> str:
    return f'href="?view={route}" data-didimdol-route="{route}" target="_self"'


def link_routes(html: str) -> str:
    for old, route in _LINKS:
        html = html.replace(old, _route_attr(route))
    for old, route in _HASH_LINKS:
        html = html.replace(old, old.replace('href="#"', _route_attr(route)))
    return html


@lru_cache(maxsize=None)
def _image_data_uri(filename: str) -> str:
    path = ROOT / 'images' / filename
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def inline_images(html: str) -> str:
    return re.sub(r'src="images/([\w.-]+\.png)"',
                  lambda m: f'src="{_image_data_uri(m.group(1))}"', html)


_SVG_RX = re.compile(r'<svg\b([^>]*)>(.*?)</svg>', re.S)


def svg_to_mask(html: str):
    """st.html은 인라인 <svg>를 지워버리므로, 같은 SVG를 CSS mask로 그리는 <span>으로 바꿉니다.
    색은 그대로 currentColor(글자색)를 따르므로 hover·활성 색 변화도 원본과 같습니다."""
    rules = []

    def repl(m):
        attrs, inner = m.group(1), m.group(2)
        get = lambda name: (re.search(name + r'="([^"]*)"', attrs) or [None, ''])[1]
        width, height, cls = get('width'), get('height'), get('class')
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"' + attrs.replace('currentColor', '#000') + '>'
               + inner.replace('currentColor', '#000') + '</svg>')
        svg = re.sub(r'\s+', ' ', svg).replace('"', "'")
        n = len(rules)
        uri = 'data:image/svg+xml,' + quote(svg, safe=" =:/,;'")
        rules.append(f'.dd-svg-{n}{{width:{width}px;height:{height}px;'
                     f'-webkit-mask:url("{uri}") center/100% 100% no-repeat;mask:url("{uri}") center/100% 100% no-repeat;}}')
        return f'<span class="{cls} dd-svg dd-svg-{n}" aria-hidden="true"></span>'

    html = _SVG_RX.sub(repl, html)
    css = ('.dd-svg{display:inline-block;flex:none;background-color:currentColor;}\n' + '\n'.join(rules)) if rules else ''
    return html, css


def _page(css_files, body: str, nonce: int = 0) -> str:
    body, svg_css = svg_to_mask(body)
    css = '\n'.join(_read(f) for f in css_files)
    css = re.sub(r'(?<![\w.#-])svg(?![\w-])', '.dd-svg', css)   # 원본 CSS의 svg 선택자도 그대로 적용
    return ('<style>' + PRETENDARD + '\n' + svg_css + '\n' + css + '\n' + _PAGE_SHIM + '</style>\n'
            f'<div class="didimdol-original" data-render="{nonce}">' + body + '</div>' + _ROUTER_JS)


def original_fragment(name: str) -> str:
    """홈(index.html)·사전진단 안내(diagnosis.html)를 원본 그대로 렌더링."""
    if name not in ('index.html', 'diagnosis.html'):
        raise ValueError('허용되지 않은 페이지입니다.')
    css = ['style.css'] + (['diagnosis.css'] if name == 'diagnosis.html' else [])
    return _page(css, inline_images(link_routes(_body(name))))


# ---------- 로그인·회원가입 (login.html) ----------
_SIGNUP_PROTO = re.compile(r"/\* 프로토타입: 가입 완료.*?return;\n", re.S)
_LOGIN_PROTO = "location.href = 'diagnosis.html';"
_INIT_PROTO = "setMode(location.hash === '#signup' ? 'signup' : 'login');"

# 클라이언트 검사(빈 칸·비밀번호 확인)를 통과하면 숨은 Streamlit 폼으로 값을 넘겨 서버에서 인증
_AUTH_BRIDGE_JS = '''
    window.__didimdolAuthSubmit = function (mode, data) {
      var holder = document.querySelector('.st-key-auth_payload input');
      var send = document.querySelector('.st-key-auth_bridge_submit button');
      if (!holder || !send) { msg.textContent = '잠시 후 다시 시도해 주세요.'; return; }
      var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(holder, JSON.stringify({ mode: mode, data: data }));
      holder.dispatchEvent(new Event('input', { bubbles: true }));
      var submitBtn = form.querySelector('.btn-submit');
      submitBtn.disabled = true;   // 중복 제출 방지 (응답이 없으면 8초 뒤 다시 활성화)
      setTimeout(function () { submitBtn.disabled = false; }, 8000);
      setTimeout(function () { send.click(); }, 120);
    };
'''


def _js_literal(value: str) -> str:
    # Escape markup characters so user-entered strings cannot close <script>.
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def auth_fragment(mode: str, flash: dict | None = None, nonce: int = 0) -> str:
    """login.html을 그대로 그리고, 제출만 실제 인증으로 연결."""
    html = _body('login.html')
    signup_call = ("window.__didimdolAuthSubmit('signup', {"
                   "nickname: document.getElementById('nickname').value,"
                   "userId: document.getElementById('userId').value,"
                   "password: pw.value, passwordConfirm: confirm.value});\n        return;\n")
    html, n1 = _SIGNUP_PROTO.subn(lambda _: signup_call, html)
    login_call = ("window.__didimdolAuthSubmit('login', {"
                  "userId: document.getElementById('userId').value, password: pw.value});")
    n2 = html.count(_LOGIN_PROTO)
    html = html.replace(_LOGIN_PROTO, login_call)
    init = f'setMode({json.dumps(mode)});'
    if flash:
        init += (f"\n    document.getElementById('userId').value = {_js_literal(flash.get('userId', ''))};"
                 f"\n    document.getElementById('nickname').value = {_js_literal(flash.get('nickname', ''))};"
                 f"\n    msg.textContent = {_js_literal(flash.get('msg', ''))};")
        if flash.get('field'):
            init += f"\n    var bad = document.getElementById({_js_literal(flash['field'])}); if (bad) {{ bad.classList.add('is-error'); bad.focus(); }}"
    n3 = html.count(_INIT_PROTO)
    html = html.replace(_INIT_PROTO, _AUTH_BRIDGE_JS + '\n    ' + init)
    if (n1, n2, n3) != (1, 1, 1):
        raise ValueError('login.html 스크립트 구조가 바뀌어 인증 연결 지점을 찾지 못했습니다.')
    html = link_routes(html)
    # 같은 오류가 반복돼도 화면이 다시 그려지도록 렌더 번호를 넣음
    return _page(['style.css', 'login.css'], html, nonce)


# ---------- Streamlit 화면용 헤더 (index.html 헤더 그대로) ----------
def _css_rules(css: str, selector_prefixes) -> str:
    """style.css에서 헤더 관련 규칙만 그대로 뽑아냄(@media 안의 규칙 포함)."""
    out, i = [], 0
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)

    def block_end(s, start):
        depth = 0
        for j in range(start, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    return j
        return len(s) - 1

    def wanted(sel):
        parts = [p.strip() for p in sel.split(',')]
        return all(any(p.startswith(x) for x in selector_prefixes) for p in parts)

    while i < len(css):
        brace = css.find('{', i)
        if brace < 0:
            break
        selector = css[i:brace].strip()
        end = block_end(css, brace)
        inner = css[brace + 1:end]
        if selector.startswith('@media'):
            sub = _css_rules(inner, selector_prefixes)
            if sub.strip():
                out.append(selector + ' {\n' + sub + '}\n')
        elif selector == ':root' or wanted(selector):
            out.append(selector + ' {' + inner + '}\n')
        i = end + 1
    return ''.join(out)


@lru_cache(maxsize=None)
def _header_parts():
    raw = _read('index.html')
    match = re.search(r'<header class="header">.*?</header>', raw, flags=re.S)
    if not match:
        raise ValueError('index.html에서 헤더를 찾지 못했습니다.')
    css = _css_rules(_read('style.css'), ('.header', '.logo', '.gnb'))
    return match.group(0), css


_NAV_ROUTE_OF_VIEW = {'diagnosis-live': 'diagnosis'}


def header_fragment(view: str, page_css: str = '') -> str:
    """홈페이지 헤더를 그대로 그리고, 현재 화면 메뉴만 활성 표시."""
    markup, css = _header_parts()
    markup = markup.replace(' class="is-active" aria-current="page"', '')
    markup = link_routes(markup)
    active = _NAV_ROUTE_OF_VIEW.get(view, view)
    tag = f'data-didimdol-route="{active}" target="_self"'
    pos = markup.find(tag, markup.find('<nav'))   # 로고가 아닌 메뉴 링크에만 활성 표시
    if pos >= 0:
        markup = markup[:pos] + tag + ' class="is-active" aria-current="page"' + markup[pos + len(tag):]
    wrap_css = """
.dd-site-header { width: 100vw; margin: 0 0 0 calc(50% - 50vw); background: #fff; word-break: keep-all; line-height: normal; }
.dd-site-header, .dd-site-header * { box-sizing: border-box; }
:where(.dd-site-header) a { color: inherit; text-decoration: none; }   /* style.css의 a 리셋과 같은 우선순위 */
.dd-site-header a:focus-visible { outline: 3px solid #1b5e3a; outline-offset: 3px; }
/* 스크롤해도 헤더 고정 (홈 화면과 같은 동작) */
[data-testid="stElementContainer"]:has(.dd-site-header) { position: sticky; top: 0; z-index: 1000; margin-bottom: 24px; }
"""
    return ('<style>' + PRETENDARD + '\n' + page_css + '\n' + css + wrap_css + '</style>'
            '<div class="dd-site-header">' + markup + '</div>' + _ROUTER_JS)
