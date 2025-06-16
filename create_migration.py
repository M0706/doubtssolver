#!/usr/bin/env python3
"""
Utility script to create new database migrations.
Usage: python create_migration.py migration_name "SQL content"

Example:
python create_migration.py add_user_profile_table "
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
"
"""

import sys
import asyncio
from app.core.migrations import migration_manager

async def create_migration():
    if len(sys.argv) < 3:
        print("Usage: python create_migration.py <migration_name> '<sql_content>'")
        print("\nExample:")
        print('python create_migration.py add_user_profile "CREATE TABLE IF NOT EXISTS profiles (id SERIAL PRIMARY KEY);"')
        sys.exit(1)
    
    migration_name = sys.argv[1]
    sql_content = sys.argv[2]
    
    try:
        migration_file = await migration_manager.create_migration(migration_name, sql_content)
        print(f"✅ Migration created successfully: {migration_file}")
        print("\nNext steps:")
        print("1. Review the migration file to ensure it's correct")
        print("2. Restart your FastAPI application to apply the migration")
        print("3. The migration will be applied automatically on startup")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nRemember: Only safe operations are allowed:")
        print("✅ CREATE TABLE")
        print("✅ ADD COLUMN") 
        print("✅ CREATE INDEX")
        print("❌ DROP TABLE/COLUMN (not allowed)")
        print("❌ DELETE/TRUNCATE (not allowed)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(create_migration()) 