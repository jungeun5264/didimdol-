"""디딤돌 Streamlit과 친구가 제작한 HTML 페이지를 연결하는 화면 전용 모듈.

- HTML·CSS 파일은 레이아웃 소스이며, 로그인/DB/진단/훈련 로직은 손대지 않습니다.
- 이 파일은 기존 app.py의 st.html(original_fragment(...), unsafe_allow_javascript=True)
  방식과 호환됩니다.
- Streamlit이 상대경로 PNG 파일을 직접 제공하지 않으므로 data URI로 삽입합니다.
"""
from pathlib import Path
from html import unescape
import base64
import json
import re

ROOT = Path(__file__).resolve().parent
ROUTES = ('home', 'diagnosis', 'diagnosis-live', 'training', 'community',
          'mypage', 'login', 'signup', 'onboarding')


def _rewrite_link(match: re.Match[str]) -> str:
    attributes, content = match.group(1), match.group(2)
    title = re.sub(r'<[^>]+>', '', content)
    title = re.sub(r'\s+', ' ', unescape(title)).strip()
    href = re.search(r'\bhref\s*=\s*["\']([^"\']+)["\']', attributes)
    address = href.group(1) if href else ''

    # Link labels take precedence over href, so the signup CTA really opens signup.
    by_label = {
        '회원가입하기': 'signup',
        '진단 시작하기': 'diagnosis-live',
        '맞춤형 심화 교육': 'training',
        '커뮤니티': 'community',
        '마이페이지': 'mypage',
        '홈': 'home',
        '사전진단': 'diagnosis',
        '디딤돌': 'home',
    }
    route = by_label.get(title)
    if route is None:
        route = {'index.html': 'home', 'diagnosis.html': 'diagnosis'}.get(address)
    if route is None:
        return match.group(0)
    # Keep original classes, aria attributes, and content (SVG included).
    attributes = re.sub(r'\s*href\s*=\s*(["\']).*?\1', '', attributes, count=1)
    attributes = re.sub(r'\s*data-didimdol-route\s*=\s*(["\']).*?\1', '', attributes)
    return (f'<a{attributes} href="?view={route}" data-didimdol-route="{route}"'
            f' target="_self">{content}</a>')


def _inline_images(body: str) -> str:
    def replace_image(match: re.Match[str]) -> str:
        relative = match.group(1)
        if not relative.startswith('images/') or '..' in Path(relative).parts:
            return match.group(0)
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(
                f'프론트엔드 이미지 파일 누락: {relative} — GitHub의 images/ 폴더에 추가하세요.'
            )
        data = base64.b64encode(path.read_bytes()).decode('ascii')
        return f'src="data:image/png;base64,{data}"'
    return re.sub(r'src="(images/[^"<>]+\.png)"', replace_image, body)


def original_fragment(name: str) -> str:
    if name not in ('index.html', 'diagnosis.html'):
        raise ValueError('허용되지 않은 페이지입니다.')
    raw = (ROOT / name).read_text(encoding='utf-8')
    match = re.search(r'<body[^>]*>(.*?)</body>', raw, flags=re.I | re.S)
    if not match:
        raise ValueError('HTML body 요소가 없습니다.')
    body = match.group(1)

    body = re.sub(r'<a\b([^>]*)>(.*?)</a>', _rewrite_link, body, flags=re.I | re.S)
    body = _inline_images(body)

    css = (ROOT / 'style.css').read_text(encoding='utf-8')
    if name == 'diagnosis.html':
        css += '\n' + (ROOT / 'diagnosis.css').read_text(encoding='utf-8')

    # For original HTML pages, use full-width page layout; don't change Python/Streamlit widgets.
    shim = """
    [data-testid="stMainBlockContainer"], .block-container { max-width:100%!important; width:100%!important; padding:0!important; }
    [data-testid="stAppViewContainer"], .stApp { background:#fff!important; }
    [data-testid="stHeader"] { display:none!important; }
    [data-testid="stToolbar"] { display:none!important; }
    #MainMenu, footer { visibility:hidden!important; }
    [data-testid="stVerticalBlock"] { gap:0!important; }
    [data-testid="stElementContainer"] { width:100%; }
    """
    # Pre-existing Streamlit hidden route buttons from app.py remain the actual click targets.
    js = """<script>
    if (!window.__didimdolRouteListener) {
      window.__didimdolRouteListener = true;
      document.addEventListener('click', function(event) {
        const link = event.target.closest('a[data-didimdol-route]');
        if (!link) return;
        const route = link.getAttribute('data-didimdol-route');
        if (!__ROUTES_JSON__.includes(route)) return;
        const target = document.querySelector('.st-key-route_' + route + ' button');
        if (target) {
          event.preventDefault();
          event.stopPropagation();
          target.click();
        }
        // When Streamlit hasn't rendered the route button, href is a fallback.
      }, true);
    }
    </script>""".replace('__ROUTES_JSON__', json.dumps(ROUTES))
    return ('<style>@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");\n' +
            css + '\n' + shim + '</style>\n<div class="didimdol-original">' + body + '</div>' + js)

