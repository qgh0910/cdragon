"""前端登录态与统一请求封装静态测试。"""

from pathlib import Path


INDEX_HTML = Path("src/shuyixiao_agent/static/index.html")


def _index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def test_login_overlay_is_initial_screen_and_app_shell_is_hidden_before_auth():
    """未登录首屏应只展示登录遮罩，业务壳默认隐藏。"""
    html = _index_html()

    assert 'id="authOverlay"' in html
    assert 'id="loginForm"' in html
    assert 'id="loginUsername"' in html
    assert 'id="loginPassword"' in html
    assert 'id="loginSubmitBtn"' in html
    assert 'id="authError"' in html
    assert 'id="appShell" class="container auth-hidden"' in html


def test_api_fetch_sets_credentials_csrf_and_handles_401():
    """统一 apiFetch 应带 Cookie、非安全方法 CSRF，并集中处理 401。"""
    html = _index_html()

    assert "async function apiFetch(" in html
    assert "const rawFetch = window.fetch.bind(window)" in html
    assert "credentials: 'same-origin'" in html
    assert "X-CSRF-Token" in html
    assert "['GET', 'HEAD', 'OPTIONS'].includes(method)" in html
    assert "if (response.status === 401 && redirectOnUnauthorized)" in html
    assert "handleUnauthorizedSession()" in html
    assert "window.fetch = apiFetch" in html


def test_auth_state_is_cleared_on_unauthorized_and_logout():
    """401 或退出登录时应清理本地用户与 CSRF 状态并回到登录页。"""
    html = _index_html()

    assert "function clearAuthSession()" in html
    assert "currentUser = null" in html
    assert "csrfToken = ''" in html
    assert "sessionStorage.removeItem('lpos_csrf_token')" in html
    assert "function showLoginScreen(" in html
    assert "handleUnauthorizedSession()" in html
    assert "async function logoutCurrentUser()" in html


def test_business_bootstrap_waits_for_authenticated_session():
    """页面初始化应先获取登录态，认证成功后再加载业务数据。"""
    html = _index_html()

    assert "window.addEventListener('load', initializeAuthState)" in html
    assert "async function initializeAuthState()" in html
    assert "async function initializeAuthenticatedApp()" in html
    assert "await initializeAuthenticatedApp()" in html
    assert "apiFetch(`${API_BASE}/api/auth/me`, { redirectOnUnauthorized: false })" in html

    bootstrap_start = html.index("async function initializeAuthenticatedApp()")
    bootstrap = html[bootstrap_start : html.index("// 自动调整文本框高度")]
    assert "loadAllCollections()" in bootstrap
    assert "loadCollaborationData()" in bootstrap
