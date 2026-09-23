import os
from dotenv import load_dotenv

load_dotenv()

# Обязательные переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Только один админ
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # Например @your_channel или -100xxxxxxxxxx
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")  # Для перенаправления в ЛС

# База данных (SQLite по умолчанию, на Railway можно Postgres)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")

# VIP по умолчанию
DEFAULT_VIP_PRICE = int(os.getenv("DEFAULT_VIP_PRICE", "150"))  # звёзд
VIP_DURATION_DAYS = 30

# Рефералка
REFERRAL_PERCENT = 15  # % от покупки реферала

# Партнёрка
PARTNER_VIEWS_REWARD = 50  # звёзд за 10к просмотров
PARTNER_VIEWS_THRESHOLD = 10000

# Скачивание
MAX_DOWNLOAD_SIZE_GB = 5
DOWNLOAD_QUALITY = "1080p"

# Cloudflare R2 (внешнее хранилище)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "narezki-kino")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")  # https://pub-xxxx.r2.dev

# Пути
DATA_DIR = "data"
MOVIES_DIR = os.path.join(DATA_DIR, "movies")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MOVIES_DIR, exist_ok=True)
