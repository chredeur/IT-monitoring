import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
import feedparser
from quart import current_app


class RSSFetcher:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.rss_fetcher')
        self.session: Optional[aiohttp.ClientSession] = None

    async def set_session(self, session: aiohttp.ClientSession):
        self.session = session

    async def fetch_feed(self, url: str) -> Optional[Dict]:
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return None

        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    return self._process_feed(feed, url)
                else:
                    self.logger.error(f"Failed to fetch {url}: HTTP {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def _process_feed(self, feed, url: str) -> Dict:
        entries = []
        for entry in feed.entries[:20]:  # Limite à 20 entrées
            processed_entry = {
                'title': getattr(entry, 'title', 'No title'),
                'link': getattr(entry, 'link', ''),
                'summary': getattr(entry, 'summary', ''),
                'published': self._parse_date(entry),
                'id': getattr(entry, 'id', entry.link if hasattr(entry, 'link') else ''),
                'author': getattr(entry, 'author', ''),
            }
            entries.append(processed_entry)

        return {
            'feed_info': {
                'title': getattr(feed.feed, 'title', 'Unknown Feed'),
                'description': getattr(feed.feed, 'description', ''),
                'url': url,
                'last_updated': datetime.now(timezone.utc).isoformat()
            },
            'entries': entries
        }

    def _parse_date(self, entry) -> str:
        # Essayer plusieurs champs de date (RSS et Atom)
        date_fields = [
            ('published_parsed', 'published'),
            ('updated_parsed', 'updated'),
            ('created_parsed', 'created'),
        ]

        for parsed_field, raw_field in date_fields:
            # Essayer le champ parsé en premier
            parsed_value = getattr(entry, parsed_field, None)
            if parsed_value:
                try:
                    dt = datetime(*parsed_value[:6], tzinfo=timezone.utc)
                    return dt.isoformat()
                except (ValueError, TypeError, IndexError):
                    pass

            # Essayer le champ brut
            raw_value = getattr(entry, raw_field, None)
            if raw_value and isinstance(raw_value, str):
                # Essayer de parser la date brute
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(raw_value)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    pass
                # Retourner tel quel si c'est déjà au format ISO
                if 'T' in raw_value or raw_value.count('-') >= 2:
                    return raw_value

        # Fallback: date actuelle
        return datetime.now(timezone.utc).isoformat()

    async def fetch_all_feeds(self) -> Dict[str, Dict]:
        results = {}

        for category_key, category_data in self.config['rss_feeds'].items():
            results[category_key] = {
                'category': category_data['category'],
                'feeds': {}
            }

            for feed_key, feed_config in category_data['feeds'].items():
                self.logger.info(f"Fetching {feed_config['name']} from {feed_config['url']}")
                feed_data = await self.fetch_feed(feed_config['url'])

                if feed_data:
                    feed_data['feed_info']['name'] = feed_config['name']
                    feed_data['feed_info']['type'] = feed_config['type']
                    results[category_key]['feeds'][feed_key] = feed_data
                else:
                    self.logger.warning(f"Failed to fetch {feed_config['name']}")

        return results