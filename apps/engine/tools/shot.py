"""用 Playwright 给前端页面截图（验证可视化渲染）。

用法：uv run python tools/shot.py [url] [out] [mode=d0|d4]
"""

import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173"
out = sys.argv[2] if len(sys.argv) > 2 else "shot.png"
mode = sys.argv[3] if len(sys.argv) > 3 else "d0"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1480, "height": 1040}, device_scale_factor=2)
    page.goto(url, wait_until="load")
    page.wait_for_timeout(1500)
    try:
        if mode == "d4":
            page.get_by_text("D4 多源破案").click(timeout=5000)
            page.wait_for_timeout(800)
            page.get_by_text("开始破案").click(timeout=5000)
        else:
            page.get_by_text("实时运行对比").click(timeout=5000)
    except Exception as exc:  # noqa: BLE001
        print(f"[shot] click failed: {exc}")
    page.wait_for_timeout(9000)
    page.screenshot(path=out, full_page=True)
    browser.close()
print(f"[shot] saved {out}")
