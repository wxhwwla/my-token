import asyncio
import os
from playwright.async_api import async_playwright, Page
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
import traceback


def get_month_year() -> tuple[int, int]:
    """
    获取当前月份和年份

    Returns:
        tuple: (month, year) 格式的元组
    """
    now = datetime.now()
    return now.month, now.year


def get_env_vars() -> dict[str, str]:
    """
    从环境变量中获取必要的配置

    Returns:
        dict: 包含 email, password, zip_path, error_path
    """

    load_dotenv()

    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")
    zip_path = os.getenv("ZIP_SAVE_PATH")
    error_path = os.getenv("ERROR_SAVE_PATH")

    # 检查有没有漏填
    if not email or not password or not zip_path or not error_path:
        raise ValueError("请检查 .env 文件，四个配置都要填完整！")
    script_dir = Path(__file__).parent
    zip_path = str(script_dir / zip_path)
    error_path = str(script_dir / error_path)      
    return {
        "email": email,
        "password": password,
        "zip_path": zip_path,
        "error_path": error_path
    }


@asynccontextmanager
async def start_chromium(headless: bool = False, slow_mo: int = 200):
    """
    启动 Chromium 浏览器上下文，返回浏览器、上下文和页面对象

    Args:
        headless: 是否无头模式 (默认 False)
        slow_mo: 慢速模式 (默认 200ms)

    Returns:
        tuple: (browser, context, page) 格式的元组
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        yield browser, context, page  # 把控制权交给调用者
            # 确保资源释放（实际上 async with 会自动处理，但显式写出来更安全）


async def sign_in(page: Page, email: str, password: str):
    # ---------- 1. 登录 ----------
    print("正在登录...")

    async def heartbeat():
        while True:
            await asyncio.sleep(3)
            print(".", end="", flush=True)
    # 启动心跳
    # -------------------------------------
    heart = asyncio.create_task(heartbeat()) 

    # 1. 打开登录页，超时给充足
    try:
        await page.goto(
            "https://platform.deepseek.com/sign_in",
            timeout=60000,
            wait_until="domcontentloaded"
            )
        print("\n登录页面加载完成")
    finally:
        # 关闭心跳
        # -------------------------------------
        heart.cancel()

    # 2. 等登录表单出现
    await page.wait_for_selector(".ds-auth-form-wrapper", timeout=15000)

    # 3. 检查是否有"密码登录"切换按钮（用 if，不是 try）
    social_btn = page.locator(".ds-sign-in-form__social-link")
    if await social_btn.count() > 0 and await social_btn.is_visible():
        await social_btn.click()
        # 等待邮箱输入框出现，确认切换成功
        await page.wait_for_selector('input[placeholder*="邮箱"]', timeout=5000)
        print("已切换到密码登录模式")
    else:
        print("已经是密码登录模式，直接填...")

    # 4. 填账号密码
    await page.fill('input[placeholder*="邮箱"]', email)
    await page.fill('input[placeholder*="密码"]', password)

    # 5. 点登录按钮
    await page.locator(".ds-button--primary.ds-button--filled").click()

    # 6. 等跳转到 usage 页面（这里唯一保留 try，因为有两种合理结果）
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    try:
        await page.wait_for_url("https://platform.deepseek.com/usage", timeout=15000)
    except PlaywrightTimeoutError:
        print("未自动跳转，手动前往 usage...")
        await page.goto("https://platform.deepseek.com/usage")
    
    # 7. 最终验证：等导出按钮出现
    await page.wait_for_selector('.ds-button--filled.ds-button--roundRect', timeout=10000)
    print("登录成功，已进入用量页面。")
    

async def download(page: Page, path: str):
    """
    下载指定月份的用量数据

    Args:
        page: 浏览器页面对象
        month: 需要下载的月份 (1-12)
        year: 需要下载的年份 (如 2026)  

    Returns:
        None: 数据将直接下载到本地 ZIP 文件，并打印预览到控制台
    """
    m, y = get_month_year()

    # 1. 选择月份
    value = f"{y}-{m}"
    await page.select_option('select.ds-native-select__select', value)
    await page.wait_for_timeout(500)

    # 2. 点击导出，捕获下载
    async with page.expect_download() as download_info:
        await page.get_by_role("button", name="导出").click()
    download = await download_info.value

    # 3. 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(path).mkdir(parents=True, exist_ok=True)
    await download.save_as(str(Path(path) / f"usage_{timestamp}.zip"))
    print(f"{timestamp} 导出完成")


async def export_deepseek_usage():
    """
    导出 DeepSeek 平台指定月份的用量数据

    Args:
        None:
    Returns:
        None: 数据将直接下载到本地 ZIP 文件，并打印预览到控制台
    """
    # 从环境变量中获取必要的配置
    env_vars = get_env_vars()
    email = env_vars["email"]
    password = env_vars["password"]
    zip_path = env_vars["zip_path"]
    error_path = env_vars["error_path"]


    # 启动浏览器上下文
    async with start_chromium(headless=False, slow_mo=200) as (browser, context, page):
        try:
            # 登录 DeepSeek 平台
            await sign_in(page, email, password)
            # 下载指定月份的用量数据
            await download(page, zip_path)
            print("导出完成！")            
        except Exception as e:
            # --- 灾难恢复：保留现场 ---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. 截图
            Path(error_path).mkdir(parents=True, exist_ok=True)

            await page.screenshot(path=f"{error_path}/error_{timestamp}.png", full_page=True)
            print(f"📸 截图已保存: error_{timestamp}.png")

            # 2. 存 HTML（可以直接用浏览器打开，看 DOM 结构）
            html_content = await page.content()
            with open(f"{error_path}/error_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 页面源码已保存: error_{timestamp}.html")

            # 3. 打印清晰的错误信息
            print(f"\n❌ 运行失败: {e}")
            traceback.print_exc()

            # 不要在这里 exit()，async with 会自动关闭浏览器

        await context.close()
        await browser.close()

        print("浏览器上下文已关闭。")


# ---------- 执行入口 ----------
if __name__ == "__main__":
    try:
        asyncio.run(export_deepseek_usage())
    except Exception as e:
        print(f"\n💥 脚本异常退出: {e}")
        traceback.print_exc()

     