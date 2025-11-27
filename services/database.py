import aiosqlite
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class Database:
    def __init__(self, db_path: str = "data/feeds.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.logger = logging.getLogger('it_monitoring.database')
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create tables."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        self.logger.info(f"Database connected: {self.db_path}")

    async def close(self):
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self.logger.info("Database connection closed")

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self._connection.executescript('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                last_update TEXT
            );

            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                UNIQUE(category_id, key)
            );

            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                entry_id TEXT NOT NULL,
                title TEXT,
                link TEXT,
                summary TEXT,
                author TEXT,
                published TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds(id),
                UNIQUE(feed_id, entry_id)
            );

            CREATE INDEX IF NOT EXISTS idx_entries_published ON entries(published DESC);
            CREATE INDEX IF NOT EXISTS idx_entries_feed_id ON entries(feed_id);
            CREATE INDEX IF NOT EXISTS idx_entries_entry_id ON entries(entry_id);
        ''')
        await self._connection.commit()

    async def get_or_create_category(self, key: str, name: str) -> int:
        """Get or create a category, return its ID."""
        cursor = await self._connection.execute(
            'SELECT id FROM categories WHERE key = ?', (key,)
        )
        row = await cursor.fetchone()

        if row:
            return row['id']

        cursor = await self._connection.execute(
            'INSERT INTO categories (key, name) VALUES (?, ?)',
            (key, name)
        )
        await self._connection.commit()
        return cursor.lastrowid

    async def get_or_create_feed(self, category_id: int, key: str, feed_info: Dict) -> int:
        """Get or create a feed, return its ID."""
        cursor = await self._connection.execute(
            'SELECT id FROM feeds WHERE category_id = ? AND key = ?',
            (category_id, key)
        )
        row = await cursor.fetchone()

        if row:
            # Update feed info
            await self._connection.execute(
                'UPDATE feeds SET name = ?, url = ?, type = ? WHERE id = ?',
                (feed_info['name'], feed_info['url'], feed_info['type'], row['id'])
            )
            await self._connection.commit()
            return row['id']

        cursor = await self._connection.execute(
            'INSERT INTO feeds (category_id, key, name, url, type) VALUES (?, ?, ?, ?, ?)',
            (category_id, key, feed_info['name'], feed_info['url'], feed_info['type'])
        )
        await self._connection.commit()
        return cursor.lastrowid

    async def add_entry(self, feed_id: int, entry: Dict) -> bool:
        """Add an entry if it doesn't exist. Returns True if new entry was added."""
        try:
            await self._connection.execute('''
                INSERT OR IGNORE INTO entries (feed_id, entry_id, title, link, summary, author, published)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                feed_id,
                entry.get('id', ''),
                entry.get('title', ''),
                entry.get('link', ''),
                entry.get('summary', ''),
                entry.get('author', ''),
                entry.get('published', '')
            ))
            await self._connection.commit()
            return self._connection.total_changes > 0
        except Exception as e:
            self.logger.error(f"Error adding entry: {e}")
            return False

    async def save_feeds_data(self, feeds_data: Dict) -> int:
        """Save feeds data to database. Returns count of new entries."""
        new_entries_count = 0
        timestamp = datetime.now(timezone.utc).isoformat()

        for category_key, category_data in feeds_data.items():
            category_id = await self.get_or_create_category(
                category_key,
                category_data['category']
            )

            # Update category timestamp
            await self._connection.execute(
                'UPDATE categories SET last_update = ? WHERE id = ?',
                (timestamp, category_id)
            )

            for feed_key, feed_data in category_data.get('feeds', {}).items():
                feed_id = await self.get_or_create_feed(
                    category_id,
                    feed_key,
                    feed_data['feed_info']
                )

                for entry in feed_data.get('entries', []):
                    if await self.add_entry(feed_id, entry):
                        new_entries_count += 1

        await self._connection.commit()
        self.logger.info(f"Saved {new_entries_count} new entries to database")
        return new_entries_count

    async def get_latest_entries(self, limit: int = 500) -> List[Dict]:
        """Get latest entries sorted by published date."""
        cursor = await self._connection.execute('''
            SELECT
                e.entry_id as id,
                e.title,
                e.link,
                e.summary,
                e.author,
                e.published,
                c.name as category,
                c.key as category_key,
                f.name as feed_name,
                f.type as feed_type
            FROM entries e
            JOIN feeds f ON e.feed_id = f.id
            JOIN categories c ON f.category_id = c.id
            ORDER BY e.published DESC
            LIMIT ?
        ''', (limit,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_categories(self) -> Dict:
        """Get all categories with their info."""
        cursor = await self._connection.execute('''
            SELECT
                c.key,
                c.name,
                c.last_update,
                COUNT(DISTINCT f.id) as feeds_count
            FROM categories c
            LEFT JOIN feeds f ON c.id = f.category_id
            GROUP BY c.id
        ''')

        rows = await cursor.fetchall()
        return {
            row['key']: {
                'name': row['name'],
                'last_update': row['last_update'],
                'feeds_count': row['feeds_count']
            }
            for row in rows
        }

    async def get_status(self) -> Dict:
        """Get database status/stats."""
        cursor = await self._connection.execute('SELECT COUNT(*) as count FROM categories')
        categories_count = (await cursor.fetchone())['count']

        cursor = await self._connection.execute('SELECT COUNT(*) as count FROM feeds')
        feeds_count = (await cursor.fetchone())['count']

        cursor = await self._connection.execute('SELECT COUNT(*) as count FROM entries')
        entries_count = (await cursor.fetchone())['count']

        cursor = await self._connection.execute(
            'SELECT MAX(last_update) as last_update FROM categories'
        )
        last_update = (await cursor.fetchone())['last_update']

        return {
            'total_categories': categories_count,
            'total_feeds': feeds_count,
            'total_entries': entries_count,
            'last_update': last_update
        }

    async def get_new_entries_since(self, since: str) -> List[Dict]:
        """Get entries added after a specific timestamp."""
        cursor = await self._connection.execute('''
            SELECT
                e.entry_id as id,
                e.title,
                e.link,
                e.summary,
                e.author,
                e.published,
                c.name as category,
                c.key as category_key,
                f.name as feed_name,
                f.type as feed_type
            FROM entries e
            JOIN feeds f ON e.feed_id = f.id
            JOIN categories c ON f.category_id = c.id
            WHERE e.created_at > ?
            ORDER BY e.published DESC
        ''', (since,))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
