"""
Database Module - MySQL operations for scraped data
"""
import mysql.connector
from mysql.connector import pooling
from typing import Dict, List, Optional, Any
import logging
from contextlib import contextmanager

from config.settings import DB_CONFIG


class Database:
    def __init__(self):
        self.logger = logging.getLogger('database')
        self._pool = None
        self._init_pool()
    
    def _init_pool(self):
        try:
            self._pool = pooling.MySQLConnectionPool(
                pool_name='scraper_pool',
                pool_size=5,
                **DB_CONFIG
            )
        except mysql.connector.Error as e:
            self.logger.error(f'Failed to create pool: {e}')
            raise
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self._pool.get_connection()
            yield conn
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def transaction(self):
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def get_or_create_manufacturer(self, name: str) -> int:
        with self.transaction() as cursor:
            cursor.execute('SELECT id FROM manufacturers WHERE name = %s', (name,))
            row = cursor.fetchone()
            if row:
                return row['id']
            cursor.execute('INSERT INTO manufacturers (name) VALUES (%s)', (name,))
            return cursor.lastrowid
    
    def get_or_create_socket(self, name: str, manufacturer_id: int) -> int:
        with self.transaction() as cursor:
            cursor.execute('SELECT id FROM sockets WHERE name = %s', (name,))
            row = cursor.fetchone()
            if row:
                return row['id']
            cursor.execute('INSERT INTO sockets (name, manufacturer_id) VALUES (%s, %s)', (name, manufacturer_id))
            return cursor.lastrowid
    
    def upsert_cpu(self, cpu_data: Dict[str, Any]) -> int:
        fields, values, updates = [], [], []
        for key, value in cpu_data.items():
            if value is not None:
                fields.append(key)
                values.append(value)
                if key != 'name':
                    updates.append(f'{key} = VALUES({key})')
        
        if not fields:
            return 0
        
        placeholders = ', '.join(['%s'] * len(values))
        field_names = ', '.join(fields)
        update_clause = ', '.join(updates) if updates else 'name = name'
        
        query = f'INSERT INTO cpus ({field_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}'
        
        with self.transaction() as cursor:
            cursor.execute(query, values)
            if cursor.lastrowid:
                return cursor.lastrowid
            cursor.execute('SELECT id FROM cpus WHERE name = %s', (cpu_data['name'],))
            row = cursor.fetchone()
            return row['id'] if row else 0
    
    def get_all_cpu_names(self) -> List[str]:
        with self.transaction() as cursor:
            cursor.execute('SELECT name FROM cpus ORDER BY name')
            return [row['name'] for row in cursor.fetchall()]
    
    def insert_benchmark_score(self, cpu_id: int, benchmark_name: str, score: float, source: str = None):
        with self.transaction() as cursor:
            cursor.execute('SELECT id FROM benchmarks WHERE name = %s', (benchmark_name,))
            row = cursor.fetchone()
            if not row:
                return
            cursor.execute('INSERT INTO cpu_benchmarks (cpu_id, benchmark_id, score, source) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE score = VALUES(score)', (cpu_id, row['id'], score, source))
    
    def insert_price(self, cpu_id: int, price: float, source: str, retailer: str = None):
        with self.transaction() as cursor:
            cursor.execute('INSERT INTO price_history (cpu_id, price, source, retailer) VALUES (%s, %s, %s, %s)', (cpu_id, price, source, retailer))
            cursor.execute('UPDATE cpus SET current_price = %s, price_updated_at = NOW() WHERE id = %s', (price, cpu_id))

    def get_cpu_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get CPU by exact name match."""
        with self.transaction() as cursor:
            cursor.execute('SELECT * FROM cpus WHERE name = %s', (name,))
            return cursor.fetchone()

    def get_cpu_by_id(self, cpu_id: int) -> Optional[Dict[str, Any]]:
        """Get CPU by ID."""
        with self.transaction() as cursor:
            cursor.execute('SELECT * FROM cpus WHERE id = %s', (cpu_id,))
            return cursor.fetchone()

    def insert_gaming_benchmark(
        self,
        cpu_id: int,
        game_name: str,
        resolution: str,
        avg_fps: float,
        one_percent_low: float = None,
        point_one_percent_low: float = None,
        gpu_used: str = None,
        settings: str = None,
        source: str = None
    ):
        """Insert gaming benchmark data."""
        with self.transaction() as cursor:
            cursor.execute('''
                INSERT INTO gaming_benchmarks
                (cpu_id, game_name, resolution, settings, avg_fps, one_percent_low,
                 point_one_percent_low, gpu_used, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    avg_fps = VALUES(avg_fps),
                    one_percent_low = VALUES(one_percent_low),
                    point_one_percent_low = VALUES(point_one_percent_low)
            ''', (cpu_id, game_name, resolution, settings, avg_fps,
                  one_percent_low, point_one_percent_low, gpu_used, source))

    def get_all_cpus(self) -> List[Dict[str, Any]]:
        """Get all CPUs with their related data."""
        with self.transaction() as cursor:
            cursor.execute('''
                SELECT c.*, m.name as manufacturer_name, s.name as socket_name
                FROM cpus c
                LEFT JOIN manufacturers m ON c.manufacturer_id = m.id
                LEFT JOIN sockets s ON c.socket_id = s.id
                ORDER BY c.name
            ''')
            return cursor.fetchall()

    def get_cpu_benchmarks(self, cpu_id: int) -> List[Dict[str, Any]]:
        """Get all benchmarks for a CPU."""
        with self.transaction() as cursor:
            cursor.execute('''
                SELECT b.name, b.unit, b.higher_is_better, cb.score, cb.source
                FROM cpu_benchmarks cb
                JOIN benchmarks b ON cb.benchmark_id = b.id
                WHERE cb.cpu_id = %s
            ''', (cpu_id,))
            return cursor.fetchall()

    def get_cpu_gaming_benchmarks(self, cpu_id: int) -> List[Dict[str, Any]]:
        """Get all gaming benchmarks for a CPU."""
        with self.transaction() as cursor:
            cursor.execute('''
                SELECT game_name, resolution, settings, avg_fps,
                       one_percent_low, point_one_percent_low, gpu_used
                FROM gaming_benchmarks
                WHERE cpu_id = %s
            ''', (cpu_id,))
            return cursor.fetchall()

    def update_scraper_progress(self, source: str, last_url: str = None,
                                 items_scraped: int = 0, status: str = 'running'):
        """Update scraper progress for resumability."""
        with self.transaction() as cursor:
            cursor.execute('''
                INSERT INTO scraper_progress (source, last_url, items_scraped, status, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    last_url = VALUES(last_url),
                    items_scraped = VALUES(items_scraped),
                    status = VALUES(status),
                    updated_at = NOW()
            ''', (source, last_url, items_scraped, status))

    def get_scraper_progress(self, source: str) -> Optional[Dict[str, Any]]:
        """Get scraper progress for resuming."""
        with self.transaction() as cursor:
            cursor.execute(
                'SELECT * FROM scraper_progress WHERE source = %s',
                (source,)
            )
            return cursor.fetchone()


_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
