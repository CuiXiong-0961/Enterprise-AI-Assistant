import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=True)

XIAOAI_API_KEY = os.getenv("XIAOAI_API_KEY")
XIAOAI_BASE_URL = os.getenv("XIAOAI_BASE_URL")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL")

BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY")
BAILIAN_BASE_URL = os.getenv("BAILIAN_BASE_URL")

LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL")

# print(XIAOAI_API_KEY)
