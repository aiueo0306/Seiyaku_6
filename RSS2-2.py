import os
import sys
import subprocess
import tempfile
import re
import time
import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ===== GitHub 上の共通関数を一時ディレクトリにクローン =====
REPO_URL = "https://github.com/aiueo0306/shared-python-env.git"
SHARED_DIR = os.path.join(tempfile.gettempdir(), "shared-python-env")

if not os.path.exists(SHARED_DIR):
    print("🔄 共通関数を初回クローン中...")
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, SHARED_DIR], check=True)
else:
    print("🔁 共通関数を更新中...")
    subprocess.run(["git", "-C", SHARED_DIR, "pull"], check=True)

sys.path.append(SHARED_DIR)

# ===== 共通関数のインポート =====
from rss_utils import generate_rss
from scraper_utils import extract_items
from browser_utils import click_button_in_order

# ===== 固定情報（学会サイト） =====
BASE_URL = "https://www.npi-inc.co.jp/medical/info/topics"
GAKKAI = "日本薬品工業(医療従事者)"

SELECTOR_TITLE = "body > table:nth-child(2) > tbody > tr:nth-child(2) > td.td_left > table > tbody > tr:nth-child(4) > td > table > tbody tr:nth-of-type(n+2)"
title_selector = ""
title_index = 0
href_selector = "a"
href_index = 0
SELECTOR_DATE = "body > table:nth-child(2) > tbody > tr:nth-child(2) > td.td_left > table > tbody > tr:nth-child(4) > td > table > tbody tr:nth-of-type(n+2)"
date_selector = "td"
date_index = 0
year_unit = "/"      # 年の後に区切り記号なし
month_unit = "/"    # 月と日の間の区切りスペース
day_unit = ""      # 日の後にカンマ

# フォーマット（%b は英語短縮月名: Jan, Feb, ... Aug）
date_format = f"%b{month_unit}%d{day_unit} %Y"

# 正規表現（英語月名 + 日 + , + 年）
date_regex = rf"([A-Za-z]{{3}}){month_unit}(\d{{1,2}}){day_unit}\s+(\d{{4}})"

# ===== ポップアップ順序クリック設定 =====
POPUP_MODE = 1  # 1: 実行 / 0: スキップ
POPUP_BUTTONS = ["はい"]  # 正確なボタン表記だけを指定
WAIT_BETWEEN_POPUPS_MS = 500
BUTTON_TIMEOUT_MS = 12000

# ===== Playwright 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    # 無人実行：headless=True のまま（UA/viewport を人間同等にするのも有効）
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        locale="ja-JP",
        viewport={"width": 1366, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "ja,en;q=0.8"},
    )
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(BASE_URL, timeout=240000)
        page.wait_for_load_state("domcontentloaded", timeout=240000)
        print("🌐 到達URL:", page.url)

        # ---- ポップアップ順に処理 ----
        if POPUP_MODE == 1 and POPUP_BUTTONS:
            for i, label in enumerate(POPUP_BUTTONS, start=1):
                handled = click_button_in_order(page, label, step_idx=i, timeout_ms=BUTTON_TIMEOUT_MS)
                if handled:
                    page.wait_for_timeout(WAIT_BETWEEN_POPUPS_MS)
                else:
                    break  # 次に進めたい場合は continue に
        else:
            print("ℹ ポップアップ処理をスキップ（POPUP_MODE=0）")

        # 本文読み込み
        page.wait_for_load_state("load", timeout=240000)

    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        raise

    print("▶ 記事を抽出しています...")
    items = extract_items(
        page,
        SELECTOR_DATE,
        SELECTOR_TITLE,
        title_selector,
        title_index,
        href_selector,
        href_index,
        BASE_URL,
        date_selector,
        date_index,
        date_format,
        date_regex,
    )

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    os.makedirs("rss_output", exist_ok=True)
    rss_path = "rss_output/Feed2-2.xml"
    generate_rss(items, rss_path, BASE_URL, GAKKAI)
    browser.close()
