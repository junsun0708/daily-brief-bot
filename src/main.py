"""Daily Brief Bot — entry point and scheduler."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Config, load_config
from src.formatter import format_briefing
from src.generator import BriefingGenerator
from src.news.fetcher import fetch_all_news
from src.slack_client import SlackBriefingClient

logger = logging.getLogger("daily-brief-bot")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_briefing(config: Config) -> bool:
    """Execute a single briefing cycle: fetch → generate → format → send.

    Returns True if briefing was sent successfully.
    """
    logger.info("=== Starting briefing cycle ===")

    # 1. Fetch news
    logger.info("Fetching news from all sources...")
    news_batches = fetch_all_news()
    total_items = sum(len(batch.items) for batch in news_batches.values())
    logger.info("Fetched %d total news items across %d categories", total_items, len(news_batches))

    # 2. Generate briefing content via LLM
    logger.info("Generating briefing content...")
    generator = BriefingGenerator(config)
    now = datetime.now(ZoneInfo(config.timezone))
    content = generator.generate_briefing(news_batches, now=now)

    # 3. Format for Slack
    logger.info("Formatting message...")
    payload = format_briefing(content)

    # 4. Send to Slack
    logger.info("Sending to Slack...")
    client = SlackBriefingClient(config)
    success = client.send_message(payload)

    if success:
        logger.info("=== Briefing sent successfully! ===")
    else:
        logger.error("=== Failed to send briefing ===")

    return success


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daily Brief Bot — 매일 아침 뉴스 브리핑을 슬랙으로 발송합니다"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="즉시 브리핑을 발송합니다 (스케줄러 없이 1회 실행)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Slack 연결 테스트만 실행합니다",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="디버그 로그를 출력합니다",
    )
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # Load config
    try:
        config = load_config()
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(
        "Config loaded — send_time=%s, timezone=%s, model=%s",
        config.send_time,
        config.timezone,
        config.openai_model,
    )

    # Test mode
    if args.test:
        client = SlackBriefingClient(config)
        if client.test_connection():
            logger.info("✅ Slack connection test passed!")
            sys.exit(0)
        else:
            logger.error("❌ Slack connection test failed!")
            sys.exit(1)

    # Immediate execution
    if args.now:
        success = run_briefing(config)
        sys.exit(0 if success else 1)

    # Scheduled mode
    logger.info(
        "Starting scheduler — briefing at %s %s daily",
        config.send_time,
        config.timezone,
    )

    scheduler = BlockingScheduler(timezone=ZoneInfo(config.timezone))

    scheduler.add_job(
        run_briefing,
        trigger=CronTrigger(
            hour=config.send_hour,
            minute=config.send_minute,
            timezone=ZoneInfo(config.timezone),
        ),
        args=[config],
        id="daily_briefing",
        name="Daily Briefing",
        misfire_grace_time=3600,  # Allow 1 hour grace period
    )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutdown signal received, stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
