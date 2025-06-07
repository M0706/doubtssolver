import os
import asyncpg
from env_vars import DATABASE_URL

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(DATABASE_URL)
            await self.create_tables()

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def get_pool(self):
        if not self.pool:
            await self.connect()
        return self.pool

    async def create_tables(self):
        sql_path = os.path.join(os.path.dirname(__file__), 'models.sql')
        with open(sql_path, 'r') as f:
            sql = f.read()
        async with self.pool.acquire() as conn:
            await conn.execute(sql)

db = Database() 