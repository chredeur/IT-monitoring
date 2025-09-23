import asyncio
import logging
from datetime import datetime, timezone

from services.data_manager import DataManager
from services.rss_fetcher import RSSFetcher


class BackgroundTaskManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.background_tasks')
        self.rss_fetcher = RSSFetcher(config)
        self.data_manager = DataManager(config)
        self.running = False
        self.task = None

    async def start(self, session):
        if self.running:
            self.logger.warning("Background tasks already running")
            return

        await self.rss_fetcher.set_session(session)
        self.running = True
        self.task = asyncio.create_task(self._run_tasks())
        self.logger.info("Background tasks started")

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
                success = await self.data_manager.save_feeds_data(feeds_data)

                if success:
                    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                    self.logger.info(f"RSS feeds fetch completed in {duration:.2f}s")
                else:
                    self.logger.error("Failed to save feeds data")
            else:
                self.logger.warning("No feeds data retrieved")

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