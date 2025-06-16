import os
import hashlib
import asyncpg
from typing import List, Dict
import pathlib
from app.core.config import DATABASE_URL

class MigrationManager:
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = pathlib.Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)

    async def init_migration_table(self, conn: asyncpg.Connection):
        """Create the migrations tracking table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> Dict[str, str]:
        """Get list of already applied migrations with their checksums"""
        rows = await conn.fetch("SELECT filename, checksum FROM schema_migrations")
        return {row['filename']: row['checksum'] for row in rows}

    def get_migration_files(self) -> List[pathlib.Path]:
        """Get all .sql migration files sorted by name"""
        migration_files = list(self.migrations_dir.glob("*.sql"))
        migration_files.sort(key=lambda x: x.name)
        return migration_files

    def calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of migration content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements, handling dollar-quoted strings properly"""
        statements = []
        current_statement = ""
        in_dollar_quote = False
        dollar_tag = ""
        i = 0
        
        while i < len(sql_content):
            char = sql_content[i]
            
            # Check for dollar-quoted string start/end
            if char == '$' and not in_dollar_quote:
                # Look for dollar tag
                j = i + 1
                while j < len(sql_content) and sql_content[j] not in ['$', ' ', '\n', '\t']:
                    j += 1
                if j < len(sql_content) and sql_content[j] == '$':
                    dollar_tag = sql_content[i:j+1]
                    in_dollar_quote = True
                    current_statement += sql_content[i:j+1]
                    i = j + 1
                    continue
            elif char == '$' and in_dollar_quote:
                # Check if this ends the dollar quote
                if sql_content[i:i+len(dollar_tag)] == dollar_tag:
                    in_dollar_quote = False
                    current_statement += dollar_tag
                    i += len(dollar_tag)
                    continue
            
            # Handle statement separation
            if char == ';' and not in_dollar_quote:
                current_statement += char
                statements.append(current_statement.strip())
                current_statement = ""
            else:
                current_statement += char
            
            i += 1
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return [stmt for stmt in statements if stmt]

    def is_safe_migration(self, sql_content: str) -> bool:
        """Check if migration only contains safe operations (additions only)"""
        dangerous_keywords = [
            'DROP TABLE', 'DROP COLUMN', 'DROP INDEX', 'DROP CONSTRAINT',
            'ALTER COLUMN', 'RENAME', 'DELETE FROM', 'TRUNCATE',
            'MODIFY COLUMN'
        ]
        
        sql_upper = sql_content.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        return True

    async def run_migrations(self, pool: asyncpg.Pool):
        """Run all pending migrations"""
        async with pool.acquire() as conn:
            # Initialize migration tracking table
            await self.init_migration_table(conn)
            
            # Get applied migrations
            applied_migrations = await self.get_applied_migrations(conn)
            
            # Get all migration files
            migration_files = self.get_migration_files()
            
            pending_migrations = []
            
            for migration_file in migration_files:
                filename = migration_file.name
                content = migration_file.read_text(encoding='utf-8')
                checksum = self.calculate_checksum(content)
                
                if filename in applied_migrations:
                    # Check if file was modified
                    if applied_migrations[filename] != checksum:
                        print(f"⚠️ Warning: Migration {filename} was modified after being applied!")
                        print("   This could indicate a problem. Skipping...")
                        continue
                else:
                    # New migration to apply
                    if not self.is_safe_migration(content):
                        print(f"❌ Unsafe migration detected in {filename}")
                        print("   Only safe operations are allowed (CREATE TABLE, ADD COLUMN, CREATE INDEX)")
                        print("   Skipping this migration for safety...")
                        continue
                    
                    pending_migrations.append((filename, content, checksum))
            
            # Apply pending migrations
            for filename, content, checksum in pending_migrations:
                try:
                    print(f"🔄 Applying migration: {filename}")
                    
                    # Execute migration in a transaction
                    async with conn.transaction():
                        # Split and execute each statement (handling dollar-quoted strings)
                        statements = self._split_sql_statements(content)
                        for statement in statements:
                            if statement.strip():
                                await conn.execute(statement)
                        
                        # Record migration as applied
                        await conn.execute(
                            "INSERT INTO schema_migrations (filename, checksum) VALUES ($1, $2)",
                            filename, checksum
                        )
                    
                    print(f"✅ Successfully applied migration: {filename}")
                    
                except Exception as e:
                    print(f"❌ Error applying migration {filename}: {e}")
                    # Don't continue with other migrations if one fails
                    raise

    async def create_migration(self, name: str, sql_content: str):
        """Create a new migration file"""
        # Generate timestamp-based filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.sql"
        migration_file = self.migrations_dir / filename
        
        # Validate it's a safe migration
        if not self.is_safe_migration(sql_content):
            raise ValueError("Migration contains unsafe operations. Only additions are allowed.")
        
        # Write migration file
        migration_file.write_text(sql_content, encoding='utf-8')
        print(f"📝 Created migration: {filename}")
        return migration_file

# Global migration manager instance
migration_manager = MigrationManager() 