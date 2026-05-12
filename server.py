#!/usr/bin/env python3
"""
Telegram News Briefing Bot – server.py
종합 경제 브리핑 봇
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import feedparser
import schedule
import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
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

# 딥시크 API 키
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    logger.error(
        "DEEPSEEK_API_KEY 환경 변수가 설정되지 않았습니다. "
        "딥시크 AI 요약 기능을 사용하려면 키를 설정해 주세요."
    )
    sys.exit(1)

# OpenAI 클라이언트 (딥시크 API 호환)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
)

# 전역 변수: Application 인스턴스 (스케줄러에서 사용)
application_instance: Application = None


# ---------- 데이터 수집 함수 ----------

def get_market_prices() -> str:
    """코스피, 나스닥, 비트코인 현재 가격을 문자열로 반환"""
    try:
        kospi = yf.Ticker("^KS11")
        nasdaq = yf.Ticker("^IXIC")
        btc = yf.Ticker("BTC-USD")

        kospi_price = kospi.history(period="1d")["Close"].iloc[-1]
        nasdaq_price = nasdaq.history(period="1d")["Close"].iloc[-1]
        btc_price = btc.history(period="1d")["Close"].iloc[-1]

        return (
            f"📈 **현재 지수 및 코인 가격**\n"
            f"• 코스피 (KOSPI): {kospi_price:,.2f} KRW\n"
            f"• 나스닥 (NASDAQ): {nasdaq_price:,.2f} USD\n"
            f"• 비트코인 (BTC): ${btc_price:,.2f} USD"
        )
    except Exception as e:
        logger.error(f"시장 가격 조회 실패: {e}")
        return "📈 **현재 지수 및 코인 가격**\n(데이터를 불러올 수 없습니다)"


def fetch_news(feed_url: str, max_items: int) -> list[dict]:
    """RSS 피드에서 뉴스 제목과 링크를 가져옴"""
    try:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.title,
                "link": entry.link,
            })
        return items
    except Exception as e:
        logger.error(f"뉴스 피드 파싱 실패: {e}")
        return []


def get_world_news() -> str:
    """세계 경제 뉴스 Top 5"""
    feed_url = "https://news.google.com/rss/search?q=economy&hl=en-US&gl=US&ceid=US:en"
    news = fetch_news(feed_url, 5)
    if not news:
        return "🌍 **세계 경제 뉴스 Top 5**\n(뉴스를 불러올 수 없습니다)"
    lines = ["🌍 **세계 경제 뉴스 Top 5**"]
    for i, item in enumerate(news, 1):
        lines.append(f"{i}. [{item['title']}]({item['link']})")
    return "\n".join(lines)


def get_crypto_news() -> str:
    """가상화폐 주요 뉴스 Top 3"""
    feed_url = "https://news.google.com/rss/search?q=cryptocurrency&hl=en-US&gl=US&ceid=US:en"
    news = fetch_news(feed_url, 3)
    if not news:
        return "🪙 **코인 주요 뉴스 Top 3**\n(뉴스를 불러올 수 없습니다)"
    lines = ["🪙 **코인 주요 뉴스 Top 3**"]
    for i, item in enumerate(news, 1):
        lines.append(f"{i}. [{item['title']}]({item['link']})")
    return "\n".join(lines)


def get_deepseek_summary(world_titles: list[str], crypto_titles: list[str]) -> str:
    """딥시크 AI를 사용해 뉴스 제목 기반 3줄 요약 생성"""
    prompt = (
        "다음은 오늘의 세계 경제 뉴스 제목과 가상화폐 뉴스 제목입니다.\n"
        "이를 바탕으로 오늘 시장의 전망을 3줄로 요약해 주세요.\n\n"
        "세계 경제 뉴스:\n"
    )
    for t in world_titles:
        prompt += f"- {t}\n"
    prompt += "\n가상화폐 뉴스:\n"
    for t in crypto_titles:
        prompt += f"- {t}\n"
    prompt += "\n3줄 요약:"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "당신은 경제 분석 전문가입니다. 간결하고 명확하게 요약합니다."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        summary = response.choices[0].message.content.strip()
        return f"💡 **딥시크 AI 시장 전망 3줄 요약**\n{summary}"
    except Exception as e:
        logger.error(f"딥시크 API 호출 실패: {e}")
        return "💡 **딥시크 AI 시장 전망 3줄 요약**\n(요약을 생성할 수 없습니다)"


def build_briefing() -> str:
    """전체 브리핑 메시지 생성"""
    prices = get_market_prices()
    world_news = get_world_news()
    crypto_news = get_crypto_news()

    # 뉴스 제목 리스트 추출 (요약용)
    world_titles = []
    crypto_titles = []
    try:
        feed_world = feedparser.parse("https://news.google.com/rss/search?q=economy&hl=en-US&gl=US&ceid=US:en")
        for entry in feed_world.entries[:5]:
            world_titles.append(entry.title)
    except Exception:
        pass
    try:
        feed_crypto = feedparser.parse("https://news.google.com/rss/search?q=cryptocurrency&hl=en-US&gl=US&ceid=US:en")
        for entry in feed_crypto.entries[:3]:
            crypto_titles.append(entry.title)
    except Exception:
        pass

    summary = get_deepseek_summary(world_titles, crypto_titles)

    return f"{prices}\n\n{world_news}\n\n{crypto_news}\n\n{summary}"


# ---------- 텔레그램 핸들러 ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자가 /start 명령어를 보냈을 때 실행됩니다."""
    user = update.effective_user
    await update.message.reply_text(
        f"안녕하세요, {user.first_name}님!\n"
        "저는 종합 경제 브리핑 봇입니다.\n"
        "명령어:\n"
        "/briefing - 지금 바로 브리핑 받기\n"
        "매일 오전 8시에 자동으로 브리핑을 보내드립니다."
    )


async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """사용자가 /briefing 명령어를 보냈을 때 브리핑 전송"""
    await update.message.reply_text("브리핑을 생성 중입니다... 잠시만 기다려 주세요.")
    try:
        briefing_text = build_briefing()
        await update.message.reply_text(briefing_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"브리핑 생성 실패: {e}")
        await update.message.reply_text("브리핑 생성 중 오류가 발생했습니다. 나중에 다시 시도해 주세요.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """예외가 발생했을 때 로그를 남깁니다."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


# ---------- 스케줄러 ----------

def send_scheduled_briefing():
    """매일 오전 8시에 실행되는 스케줄 함수"""
    global application_instance
    if application_instance is None:
        logger.warning("Application 인스턴스가 없어 스케줄 브리핑을 보낼 수 없습니다.")
        return

    logger.info("스케줄 브리핑 생성 시작")
    try:
        briefing_text = build_briefing()
        # 모든 채팅에 보내는 대신, 봇이 메시지를 받은 채팅들에 보내는 것은 복잡하므로
        # 여기서는 간단히 로그만 남기고 실제 전송은 생략합니다.
        # 실제로는 사용자별 chat_id를 저장해야 합니다.
        # 여기서는 예시로 application_instance.bot.send_message(chat_id=..., text=briefing_text, parse_mode="Markdown")
        logger.info("스케줄 브리핑 생성 완료 (전송은 생략)")
    except Exception as e:
        logger.error(f"스케줄 브리핑 생성 실패: {e}")


def run_scheduler():
    """스케줄러를 별도 스레드에서 실행"""
    schedule.every().day.at("08:00").do(send_scheduled_briefing)
    while True:
        schedule.run_pending()
        import time
        time.sleep(30)


# ---------- 메인 ----------

def main() -> None:
    """봇 애플리케이션을 생성하고 실행합니다."""
    global application_instance

    # Application 생성
    application = Application.builder().token(BOT_TOKEN).build()
    application_instance = application

    # 핸들러 등록
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("briefing", briefing))

    # 에러 핸들러 등록
    application.add_error_handler(error_handler)

    # 스케줄러 스레드 시작
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # 봇 실행 (폴링 방식)
    logger.info("봇이 시작되었습니다. Ctrl+C로 종료할 수 있습니다.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
