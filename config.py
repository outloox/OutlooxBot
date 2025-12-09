import os

def get_admins():
    admins_str = os.environ.get("ADMIN_IDS", "")
    if not admins_str:
        return []
    return [int(admin_id.strip()) for admin_id in admins_str.split(',')]

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = get_admins()

FIREBASE_DB_URL = "https://new-prototype-nwxqu-default-rtdb.europe-west1.firebasedatabase.app/"
WEB_APP_URL = "https://outloox.github.io/"

USER_DAILY_LIMIT = 20
BACKUP_FILE_PATH = "valid_accounts_backup.txt"
REQUEST_TIMEOUT = 25
CONCURRENT_TASKS = 10
ANTISPAM_DELAY = 5
PROXY_CHECK_TIMEOUT = 7

COMMON_COUNTRY_NAMES = {
    "Korea, Republic of": "South Korea", "Iran, Islamic Republic of": "Iran",
    "Venezuela, Bolivarian Republic of": "Venezuela", "Bolivia, Plurinational State of": "Bolivia",
    "Russian Federation": "Russia", "United Kingdom": "UK", "United States": "USA",
    "Syrian Arab Republic": "Syria", "Viet Nam": "Vietnam", "Taiwan, Province of China": "Taiwan"
}

SERVICE_DOMAINS = {
    'facebookmail.com': 'Facebook', 'mail.instagram.com': 'Instagram', 'account.tiktok.com': 'TikTok',
    'x.com': 'Twitter/X', 'paypal.com': 'PayPal', 'binance.com': 'Binance', 'account.netflix.com': 'Netflix',
    'txn-email.playstation.com': 'PlayStation', 'id.supercell.com': 'Supercell', 'acct.epicgames.com': 'Epic Games',
    'spotify.com': 'Spotify', 'rockstargames.com': 'Rockstar', 'engage.xbox.com': 'Xbox', 'google.com': 'Google',
    'steampowered.com': 'Steam', 'roblox.com': 'Roblox', 'e.ea.com': 'EA', 'tm.openai.com': 'OpenAI/ChatGPT',
    'tencentgames.com': 'Tencent', 'amazon.com': 'Amazon', 'discord.com': 'Discord', 'crunchyroll.com': 'Crunchyroll',
    'linkedin.com': 'LinkedIn', 'github.com': 'GitHub', 'twitch.tv': 'Twitch', 'ubisoft.com': 'Ubisoft',
    'riotgames.com': 'Riot Games', 'blizzard.com': 'Blizzard', 'disneyplus.com': 'Disney+', 'hulu.com': 'Hulu',
    'apple.com': 'Apple ID', 'ebay.com': 'eBay', 'aliexpress.com': 'AliExpress', 'booking.com': 'Booking.com',
    'airbnb.com': 'Airbnb', 'uber.com': 'Uber', 'microsoft.com': 'Microsoft', 'office.com': 'Office 365'
}
