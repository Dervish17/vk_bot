from dotenv import load_dotenv
import re
import os

load_dotenv()
TOKEN = os.getenv("VK_TOKEN_TEST")
GROUP_ID = 115581151
MAX_FIO_LENGTH = 60
MIN_FIO_LENGTH = 2
BAD_WORDS = {
    "хуй", "пизд", "еб", "бля", "сука", "мудак", "гандон", "чмо",
    "fuck", "shit", "bitch", "asshole", "cunt", "dick"
}
FIO_REGEX = re.compile(r"^[А-Яа-яЁёA-Za-z\s\-]+$")