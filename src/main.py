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


def run_briefing(config: Config, dry_run: bool = False) -> bool:
    """Execute a single briefing cycle: fetch → generate → format → send."""
    logger.info("=== Starting briefing cycle %s===", "(DRY RUN) " if dry_run else "")

    try:
        logger.info("Fetching news from all sources...")
        news_batches = fetch_all_news()
        total_items = sum(len(batch.items) for batch in news_batches.values())
        logger.info("Fetched %d total news items across %d categories", total_items, len(news_batches))

        logger.info("Generating briefing content...")
        generator = BriefingGenerator(config)
        now = datetime.now(ZoneInfo(config.timezone))
        content = generator.generate_briefing(news_batches, now=now)

        logger.info("Formatting message...")
        payload = format_briefing(content)

        if dry_run:
            import json
            print("\n" + "=" * 60)
            print("DRY RUN — Slack message payload:")
            print("=" * 60)
            for block in payload["blocks"]:
                if block["type"] == "header":
                    print(f"\n### {block['text']['text']}")
                elif block["type"] == "section":
                    print(block["text"]["text"])
                elif block["type"] == "divider":
                    print("-" * 40)
                elif block["type"] == "context":
                    print(f"  {block['elements'][0]['text']}")
            print("=" * 60)
            logger.info("=== Dry run complete ===")
            return True

        logger.info("Sending to Slack...")
        client = SlackBriefingClient(config)

        if not client.validate_channel():
            logger.error("Channel validation failed — aborting send")
            return False

        success = client.send_message(payload)

        if success:
            logger.info("=== Briefing sent successfully! ===")
        else:
            logger.error("=== Failed to send briefing ===")

        return success

    except Exception:
        logger.exception("Briefing cycle failed with unexpected error")
        return False


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
        "--dry-run",
        action="store_true",
        help="브리핑을 생성하되 Slack 발송 없이 터미널에 출력합니다",
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

    if args.dry_run:
        success = run_briefing(config, dry_run=True)
        sys.exit(0 if success else 1)

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
