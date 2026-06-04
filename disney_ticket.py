"""
東京ディズニーリゾート チケット自動購入スクリプト
対象: 首都圏ウィークデーパスポート (2026年6月5日 金曜日 / 東京ディズニーシー)

使い方:
  1. python3 disney_ticket.py を実行
  2. ブラウザでログイン → チケット購入ページ(人数選択画面)まで手動で移動
  3. ターミナルに戻りEnterを押すと①から自動操作開始
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

TICKET_URL = "https://plan.tokyodisneyresort.jp/2/4/?lang=ja"
MAX_RETRIES = 999


async def run(playwright):
    browser = await playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        locale="ja-JP",
        timezone_id="Asia/Tokyo",
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        },
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        window.chrome = { runtime: {} };
    """)
    page = await context.new_page()

    # ── 手動操作待機 ──────────────────────────────────────────────────
    await page.goto("https://www.tokyodisneyresort.jp/", wait_until="domcontentloaded", timeout=30000)

    print("\n" + "=" * 55)
    print("【手順】")
    print("  1. ブラウザでディズニーアカウントにログイン")
    print(f"  2. 以下のURLを開いてチケット人数選択画面まで進む")
    print(f"     {TICKET_URL}")
    print("  3. 人数選択画面が表示されたらターミナルに戻る")
    print("  4. Enterキーを押すと①から自動操作を開始します")
    print("=" * 55)
    input("\n▶ 準備ができたらEnterキーを押してください...")
    print("\n自動操作を開始します！\n")

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"=== 試行 {attempt} 回目 ===")
        try:
            result = await attempt_purchase(page)
            if result == "success":
                print("✅ カートへの追加に成功しました！")
                break
            elif result == "soldout":
                print("❌ 売り切れ。リトライします...\n")
                await asyncio.sleep(1)
            else:
                print(f"⚠ 予期しない結果: {result}")
                break
        except Exception as e:
            print(f"エラー発生: {e}\n")
            await asyncio.sleep(2)

    input("\nEnterキーで終了...")
    await browser.close()


async def attempt_purchase(page) -> str:
    """1回の購入試行。戻り値: 'success' / 'soldout'"""

    # ── ① 人数 +1 → 次へ ────────────────────────────────────────────
    print("① 人数 +1...")
    await page.wait_for_timeout(2000)

    # デバッグ: ページ上の全ボタンテキストを出力
    buttons = await page.locator("button").all()
    btn_texts = []
    for b in buttons:
        txt = (await b.inner_text()).strip()
        cls = await b.get_attribute("class") or ""
        aria = await b.get_attribute("aria-label") or ""
        btn_texts.append(f"  text='{txt}' class='{cls}' aria='{aria}'")
    print("  [DEBUG] ページ上のボタン一覧:")
    print("\n".join(btn_texts[:30]))

    plus_btn = page.locator(
        'button[data-testid="plus"], button.plus, '
        '[aria-label*="追加"], button:has-text("+")'
    ).first
    await plus_btn.wait_for(state="visible", timeout=15000)
    await plus_btn.click()

    next_btn = page.locator(
        'button:has-text("次へ"), a:has-text("次へ"), [data-testid="next"]'
    ).first
    await next_btn.wait_for(state="visible", timeout=10000)
    await next_btn.click()

    # ── ② 東京ディズニーシー ─────────────────────────────────────────
    print("② 東京ディズニーシー選択...")
    sea_btn = page.locator(
        'button:has-text("東京ディズニーシー"), '
        'label:has-text("東京ディズニーシー"), '
        '[alt*="東京ディズニーシー"], img[src*="sea"]'
    ).first
    await sea_btn.wait_for(state="visible", timeout=15000)
    await sea_btn.click()

    # ── ③ カレンダー 2026年6月5日(金) ──────────────────────────────
    print("③ 2026年6月5日(金)選択...")
    await page.wait_for_timeout(1000)
    await ensure_calendar_month(page, year=2026, month=6)

    day_cell = page.locator(
        '[data-date="2026-06-05"], '
        'button[aria-label*="6月5日"], '
        'button[aria-label*="June 5"], '
        'td:has-text("5")'
    ).first
    await day_cell.wait_for(state="visible", timeout=10000)
    await day_cell.click()

    # ── ④ 首都圏ウィークデーパスポート ──────────────────────────────
    print("④ 首都圏ウィークデーパスポート選択...")
    radio = page.locator(
        'label:has-text("首都圏ウィークデーパスポート") input[type="radio"], '
        'input[type="radio"][value*="weekday"]'
    ).first
    if not await radio.count():
        radio = page.locator('label:has-text("首都圏ウィークデーパスポート")').first
    await radio.wait_for(state="visible", timeout=15000)
    await radio.click()

    # ── ⑤ 大人(18歳以上) +1 ────────────────────────────────────────
    print("⑤ 大人(18歳以上) +1...")
    adult_section = page.locator(
        ':has-text("大人（18歳以上）"), :has-text("大人(18歳以上)")'
    ).last
    adult_plus = adult_section.locator(
        'button:has-text("+"), button[data-action="plus"]'
    ).first
    if not await adult_plus.count():
        adult_plus = page.locator(
            'button[data-testid="adult-plus"], button.adult-plus'
        ).first
    await adult_plus.wait_for(state="visible", timeout=10000)
    await adult_plus.click()

    # ── ⑥ 「確認した」チェックボックス ─────────────────────────────
    print("⑥ 確認したチェックボックスON...")
    confirm_cb = page.locator(
        'label:has-text("確認した") input[type="checkbox"], '
        'input[type="checkbox"][id*="confirm"]'
    ).first
    if not await confirm_cb.count():
        confirm_cb = page.locator('label:has-text("確認した")').first
    await confirm_cb.wait_for(state="visible", timeout=10000)
    await confirm_cb.scroll_into_view_if_needed()
    await confirm_cb.click()

    # ── ⑦ カートに追加する ──────────────────────────────────────────
    print("⑦ カートに追加する...")
    cart_btn = page.locator(
        'button:has-text("カートに追加"), a:has-text("カートに追加")'
    ).first
    await cart_btn.wait_for(state="visible", timeout=10000)
    await cart_btn.scroll_into_view_if_needed()
    await cart_btn.click()

    # ── 結果判定 ────────────────────────────────────────────────────
    print("  結果判定中...")
    try:
        soldout_msg = page.locator(
            ':has-text("売り切れました"), :has-text("条件を変更してやりなおしてください")'
        )
        await soldout_msg.wait_for(state="visible", timeout=8000)

        # 売り切れ → 初めからやり直す → 人数選択画面に戻る
        retry_btn = page.locator(
            'button:has-text("初めからやり直す"), a:has-text("初めからやり直す")'
        ).first
        if await retry_btn.count():
            await retry_btn.click()
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1000)
        return "soldout"

    except PlaywrightTimeoutError:
        return "success"


async def ensure_calendar_month(page, year: int, month: int):
    """カレンダーが指定年月を表示するまで次月ボタンをクリックする"""
    for _ in range(24):
        content = await page.content()
        if any(t in content for t in [f"{year}年{month}月", f"{year}/{month:02d}", f"{year}-{month:02d}"]):
            return
        next_btn = page.locator(
            'button[aria-label*="次の月"], button[aria-label*="next"], '
            'button.calendar-next, button:has-text(">")'
        ).first
        if await next_btn.count():
            await next_btn.click()
            await page.wait_for_timeout(500)
        else:
            break


async def main():
    async with async_playwright() as playwright:
        await run(playwright)


if __name__ == "__main__":
    asyncio.run(main())
