import logging
from datetime import datetime, timezone
from typing import Dict, List

from services.database import Database


class DataManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.data_manager')
        self.db: Database = config.get('database')

    async def save_feeds_data(self, feeds_data: Dict) -> bool:
        """Save feeds data to database."""
        try:
            await self.db.save_feeds_data(feeds_data)
            self.logger.info("Feeds data saved to database")
            return True
        except Exception as e:
            self.logger.error(f"Error saving feeds data: {e}")
            return False

    async def get_latest_entries(self, limit: int = 500) -> List[Dict]:
        """Get latest entries from database."""
        try:
            return await self.db.get_latest_entries(limit)
        except Exception as e:
            self.logger.error(f"Error getting latest entries: {e}")
            return []

    async def get_categories(self) -> Dict:
        """Get all categories."""
        try:
            return await self.db.get_categories()
        except Exception as e:
            self.logger.error(f"Error getting categories: {e}")
            return {}

    async def get_status(self) -> Dict:
        """Get database status."""
        try:
            return await self.db.get_status()
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return {
                'total_categories': 0,
                'total_feeds': 0,
                'total_entries': 0,
                'last_update': None
            }

    def get_new_entries(self, old_data: Dict, new_data: Dict) -> List[Dict]:
        """
        Compare old and new data to find new entries.
        Used for Discord notifications.
        """
        new_entries = []

        existing_ids = set()
        for category_key, category_data in old_data.items():
            for feed_key, feed_data in category_data.get('feeds', {}).items():
                for entry in feed_data.get('entries', []):
                    existing_ids.add(entry.get('id'))

        for category_key, category_data in new_data.items():
            for feed_key, feed_data in category_data.get('feeds', {}).items():
                feed_info = feed_data.get('feed_info', {})
                for entry in feed_data.get('entries', []):
                    entry_id = entry.get('id')
                    if entry_id and entry_id not in existing_ids:
                        enriched_entry = entry.copy()
                        enriched_entry['category'] = category_data.get('category', category_key)
                        enriched_entry['category_key'] = category_key
                        enriched_entry['feed_name'] = feed_info.get('name', feed_key)
                        enriched_entry['feed_type'] = feed_info.get('type', 'unknown')
                        new_entries.append(enriched_entry)

        return new_entries
