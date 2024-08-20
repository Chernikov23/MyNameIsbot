import os 
from dotenv import load_dotenv

TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],  # Подключаем модели
            "default_connection": "default",
        },
    },
}

load_dotenv()

TOKEN = os.getenv('TOKEN')
PASSWORD = os.getenv('PASSWORD')

