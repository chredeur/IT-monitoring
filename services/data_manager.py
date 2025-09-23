import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class DataManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.data_manager')
        self.data_dir = Path(config['storage']['data_dir'])
        self.feeds_file = Path(config['storage']['feeds_file'])
        self.user_activity_file = Path(config['storage']['user_activity_file'])

        self._ensure_directories()

    def _ensure_directories(self):
        self.data_dir.mkdir(exist_ok=True)

    async def save_feeds_data(self, feeds_data: Dict) -> bool:
        try:
            current_data = await self.load_feeds_data()

            timestamp = datetime.now(timezone.utc).isoformat()

            for category_key, category_data in feeds_data.items():
                if category_key not in current_data:
                    current_data[category_key] = {
                        'category': category_data['category'],
                        'feeds': {},
                        'last_update': timestamp
                    }

                current_data[category_key]['last_update'] = timestamp

                for feed_key, feed_data in category_data['feeds'].items():
                    if feed_key not in current_data[category_key]['feeds']:
                        current_data[category_key]['feeds'][feed_key] = {
                            'feed_info': feed_data['feed_info'],
                            'entries': []
                        }

                    current_data[category_key]['feeds'][feed_key]['feed_info'] = feed_data['feed_info']

                    existing_entries = current_data[category_key]['feeds'][feed_key]['entries']
                    new_entries = feed_data['entries']

                    existing_ids = {entry['id'] for entry in existing_entries}

                    for entry in new_entries:
                        if entry['id'] not in existing_ids:
                            existing_entries.insert(0, entry)

                    current_data[category_key]['feeds'][feed_key]['entries'] = existing_entries[:50]

            with open(self.feeds_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Feeds data saved to {self.feeds_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving feeds data: {e}")
            return False

    async def load_feeds_data(self) -> Dict:
        try:
            if self.feeds_file.exists():
                with open(self.feeds_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading feeds data: {e}")
            return {}

    async def get_category_data(self, category: str) -> Optional[Dict]:
        data = await self.load_feeds_data()
        return data.get(category)

    async def get_feed_data(self, category: str, feed: str) -> Optional[Dict]:
        category_data = await self.get_category_data(category)
        if category_data and 'feeds' in category_data:
            return category_data['feeds'].get(feed)
        return None

    async def get_latest_entries(self, limit: int = 20) -> List[Dict]:
        data = await self.load_feeds_data()
        all_entries = []

        for category_key, category_data in data.items():
            for feed_key, feed_data in category_data.get('feeds', {}).items():
                for entry in feed_data.get('entries', []):
                    entry_with_meta = entry.copy()
                    entry_with_meta['category'] = category_data['category']
                    entry_with_meta['feed_name'] = feed_data['feed_info']['name']
                    entry_with_meta['feed_type'] = feed_data['feed_info']['type']
                    all_entries.append(entry_with_meta)

        all_entries.sort(key=lambda x: x['published'], reverse=True)
        return all_entries[:limit]

    async def save_user_activity(self, user_ip: str, action: str, data: Dict = None) -> bool:
        try:
            activity = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_ip': user_ip,
                'action': action,
                'data': data or {}
            }

            activities = await self.load_user_activities()
            activities.append(activity)

            activities = activities[-1000:]

            with open(self.user_activity_file, 'w', encoding='utf-8') as f:
                json.dump(activities, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            self.logger.error(f"Error saving user activity: {e}")
            return False

    async def load_user_activities(self) -> List[Dict]:
        try:
            if self.user_activity_file.exists():
                with open(self.user_activity_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Error loading user activities: {e}")
            return []

    async def get_user_last_seen(self, user_ip: str) -> Optional[str]:
        activities = await self.load_user_activities()
        for activity in reversed(activities):
            if activity['user_ip'] == user_ip:
                return activity['timestamp']
        return None