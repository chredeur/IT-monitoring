import asyncio
import logging
from datetime import datetime, timezone

from services.data_manager import DataManager
from services.rss_fetcher import RSSFetcher
from services.discord_notifier import DiscordNotifier


class BackgroundTaskManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.background_tasks')
        self.rss_fetcher = RSSFetcher(config)
        self.data_manager = DataManager(config)
        self.discord_notifier = DiscordNotifier(config)
        self.running = False
        self.task = None
        self._first_run = True
        self._last_fetch_time = None

    async def start(self, session):
        if self.running:
            self.logger.warning("Background tasks already running")
            return

        await self.rss_fetcher.set_session(session)
        await self.discord_notifier.set_session(session)
        self.running = True
        self.task = asyncio.create_task(self._run_tasks())
        self.logger.info("Background tasks started")

        if self.discord_notifier.is_enabled():
            self.logger.info("Discord notifications enabled")

    async def stop(self):
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.logger.info("Background tasks stopped")

    async def _run_tasks(self):
        fetch_interval = self.config.get('fetch_interval', 300)

        while self.running:
            try:
                await self._fetch_all_feeds()
                await asyncio.sleep(fetch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background task: {e}")
                await asyncio.sleep(60)

    async def _fetch_all_feeds(self):
        self.logger.info("Starting RSS feeds fetch")
        start_time = datetime.now(timezone.utc)

        try:
            feeds_data = await self.rss_fetcher.fetch_all_feeds()

            if feeds_data:
                db = self.config.get('database')

                # Get entries before save for Discord notifications
                new_entries_for_discord = []
                if not self._first_run and self.discord_notifier.is_enabled():
                    # Get current entry IDs from database
                    current_entries = await db.get_latest_entries(10000)
                    existing_ids = {e['id'] for e in current_entries}

                    # Find new entries
                    for category_key, category_data in feeds_data.items():
                        for feed_key, feed_data in category_data.get('feeds', {}).items():
                            feed_info = feed_data.get('feed_info', {})
                            for entry in feed_data.get('entries', []):
                                if entry.get('id') not in existing_ids:
                                    enriched = entry.copy()
                                    enriched['category'] = category_data.get('category', category_key)
                                    enriched['category_key'] = category_key
                                    enriched['feed_name'] = feed_info.get('name', feed_key)
                                    enriched['feed_type'] = feed_info.get('type', 'unknown')
                                    new_entries_for_discord.append(enriched)

                # Save to database
                new_count = await db.save_feeds_data(feeds_data)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                self.logger.info(f"RSS feeds fetch completed in {duration:.2f}s ({new_count} new entries)")

                # Send Discord notifications
                if new_entries_for_discord:
                    self.logger.info(f"Sending Discord notifications for {len(new_entries_for_discord)} entries")
                    results = await self.discord_notifier.notify_new_entries(new_entries_for_discord)
                    self.logger.info(f"Discord notifications: {results['sent']} sent, {results['failed']} failed")

            else:
                self.logger.warning("No feeds data retrieved")

            if self._first_run:
                self._first_run = False
                self.logger.info("First run completed, future new entries will trigger notifications")

            self._last_fetch_time = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            self.logger.error(f"Error fetching RSS feeds: {e}")

    async def force_fetch(self):
        if not self.running:
            self.logger.warning("Background tasks not running, cannot force fetch")
            return False

        try:
            await self._fetch_all_feeds()
            return True
        except Exception as e:
            self.logger.error(f"Error in force fetch: {e}")
            return False
