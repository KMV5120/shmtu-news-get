"""
CAS 统一认证 + 会话管理

策略：requests 处理 CAS 登录（已验证稳定） → 将 service ticket URL
传给 Playwright 直接打开，从而获得已认证的门户页面。
"""

import io
import pickle
import re
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import (
    CAS_LOGIN_URL,
    CAS_CAPTCHA_URL,
    PORTAL_SERVICE,
    SESSION_FILE,
    USER_AGENT,
    REQUEST_TIMEOUT,
    USERNAME,
    PASSWORD,
)


def _detect_proxy():
    import urllib.request
    proxies = urllib.request.getproxies()
    if not proxies:
        return None
    for key in ("http", "https"):
        url = proxies.get(key, "")
        if url:
            if url.startswith("https://"):
                url = url.replace("https://", "http://", 1)
            return url
    return None


def _create_requests_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    s.verify = False
    s.trust_env = False
    proxy = _detect_proxy()
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
        print(f"[网络] 代理: {proxy}")
    else:
        print("[网络] 直连")
    return s


def _get_captcha_image(session: requests.Session) -> bytes:
    resp = session.get(CAS_CAPTCHA_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.content


def _show_captcha(image_bytes: bytes):
    try:
        Image.open(io.BytesIO(image_bytes)).show()
        print("[提示] 验证码图片已打开。")
    except Exception:
        p = Path("captcha.png")
        p.write_bytes(image_bytes)
        print(f"[提示] 验证码已保存到 {p.resolve()}")


def _get_execution_token(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("input", {"name": "execution"})
    if tag is None:
        raise ValueError("无法找到 execution token")
    return tag.get("value", "")


def _do_cas_login(session: requests.Session, username: str, password: str,
                  captcha: str, execution: str) -> str | None:
    """
    提交 CAS 登录表单。
    返回 service ticket 重定向 URL，失败返回 None。
    """
    resp = session.post(
        f"{CAS_LOGIN_URL}?service={PORTAL_SERVICE}",
        data={
            "username": username,
            "password": password,
            "validateCode": captcha,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        },
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )

    if resp.status_code in (301, 302):
        location = resp.headers.get("Location", "")
        if "ticket=" in location:
            return location
        if "my.shmtu.edu.cn" in location:
            return location

    soup = BeautifulSoup(resp.text, "lxml")
    error = soup.find(class_=re.compile("error|alert|warn", re.I))
    if error:
        print(f"[登录失败] {error.get_text(strip=True)}")
    else:
        print("[登录失败] 验证码或密码错误")
    return None


def login_and_get_portal_url() -> str:
    """
    用 requests 完成 CAS 登录，返回带 service ticket 的门户 URL。

    Returns:
        "https://my.shmtu.edu.cn/sopcb/?ticket=ST-xxxx"
    """
    session = _create_requests_session()
    login_url = f"{CAS_LOGIN_URL}?service={PORTAL_SERVICE}"

    # 1. GET 登录页
    print("[登录] 访问 CAS 登录页...")
    resp = session.get(login_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    execution = _get_execution_token(resp.text)

    # 2. 获取验证码
    captcha_bytes = _get_captcha_image(session)
    _show_captcha(captcha_bytes)

    # 3. 提交登录
    for attempt in range(1, 4):
        code = input(f"[登录] 请输入验证码（第 {attempt}/3 次）: ").strip()
        if not code:
            continue

        ticket_url = _do_cas_login(session, USERNAME, PASSWORD, code, execution)
        if ticket_url:
            print(f"[登录] CAS 认证成功！")
            return ticket_url

        if attempt < 3:
            print("[登录] 刷新验证码...")
            captcha_bytes = _get_captcha_image(session)
            _show_captcha(captcha_bytes)
            resp = session.get(login_url, timeout=REQUEST_TIMEOUT)
            execution = _get_execution_token(resp.text)

    raise RuntimeError("登录失败：超过最大重试次数")


def clear_session():
    """Playwright session 不需要持久化，每次重新登录"""
    pass

# ============================================================
# 独立测试
# ============================================================
if __name__ == "__main__":
    url = login_and_get_portal_url()
    print(f"Portal URL: {url}")
