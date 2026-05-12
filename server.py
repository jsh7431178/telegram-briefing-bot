#!/usr/bin/env python3
"""
Telegram News Briefing Bot – server.py
뼈대 코드: /start 명령어와 에코 기능만 포함.
"""

import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 봇 토큰 (환경 변수에서 가져오거나 직접 입력)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error(
        "TELEGRAM_BOT_TOKEN 환경 변수가 설정되지 않았습니다. "
        "봇을 실행하려면 토큰을 설정해 주세요."
    )
    sys.exit(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자가 /start 명령어를 보냈을 때 실행됩니다."""
    user = update.effective_user
    await update.message.reply_text(
        f"안녕하세요, {user.first_name}님!\n"
        "저는 뉴스 브리핑 봇입니다. 아직 뉴스 기능은 구현되지 않았습니다.\n"
        "보내신 메시지를 그대로 돌려드립니다."
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자가 보낸 텍스트 메시지를 그대로 응답합니다."""
    user_text = update.message.text
    await update.message.reply_text(f"에코: {user_text}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """예외가 발생했을 때 로그를 남깁니다."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main() -> None:
    """봇 애플리케이션을 생성하고 실행합니다."""
    # Application 생성
    application = Application.builder().token(BOT_TOKEN).build()

    # 핸들러 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # 에러 핸들러 등록
    application.add_error_handler(error_handler)

    # 봇 실행 (폴링 방식)
    logger.info("봇이 시작되었습니다. Ctrl+C로 종료할 수 있습니다.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
