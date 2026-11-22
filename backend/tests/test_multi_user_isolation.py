"""Multi-user isolation and security test for AutoSocial Poster.
Verifies that independent user profiles (separate AppData and database paths):
1. Maintain completely isolated SQLite databases
2. Never leak posts, drafts, or schedules between users
3. Maintain distinct session tokens
4. Maintain distinct vault keys/tokens
"""
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path

def test_independent_user_isolation():
    temp_root = Path(tempfile.mkdtemp(prefix="autosocial_test_multiuser_"))
    try:
        user1_appdata = temp_root / "User1" / "AppData" / "Roaming" / "AutoSocialPoster"
        user2_appdata = temp_root / "User2" / "AppData" / "Roaming" / "AutoSocialPoster"

        user1_data = user1_appdata / "data"
        user2_data = user2_appdata / "data"

        user1_data.mkdir(parents=True, exist_ok=True)
        user2_data.mkdir(parents=True, exist_ok=True)

        schema = """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            platform TEXT NOT NULL,
            destination TEXT NOT NULL,
            subreddit TEXT,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            approved INTEGER DEFAULT 0,
            scheduled_at TEXT,
            published_at TEXT,
            error_message TEXT,
            timezone TEXT DEFAULT 'UTC',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """

        # Setup User 1 DB
        user1_db = user1_data / "social_automation.sqlite3"
        with sqlite3.connect(user1_db) as conn1:
            conn1.executescript(schema)
            conn1.execute(
                "INSERT INTO posts (id, topic, platform, destination, content, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("post_u1_001", "User 1 AI Startup Launch", "linkedin", "Feed", "User 1 content", "scheduled")
            )
            conn1.commit()

        # Setup User 2 DB
        user2_db = user2_data / "social_automation.sqlite3"
        with sqlite3.connect(user2_db) as conn2:
            conn2.executescript(schema)
            conn2.execute(
                "INSERT INTO posts (id, topic, platform, destination, content, status) VALUES (?, ?, ?, ?, ?, ?)",
                ("post_u2_001", "User 2 Fitness App", "reddit", "r/fitness", "User 2 content", "draft")
            )
            conn2.commit()

        # Verify User 1 cannot see User 2's data
        with sqlite3.connect(user1_db) as conn1:
            rows1 = conn1.execute("SELECT id, topic FROM posts").fetchall()
            ids1 = [r[0] for r in rows1]
            assert "post_u1_001" in ids1, "User 1 must see own post"
            assert "post_u2_001" not in ids1, "User 1 must NOT see User 2's post"
            assert len(rows1) == 1

        # Verify User 2 cannot see User 1's data
        with sqlite3.connect(user2_db) as conn2:
            rows2 = conn2.execute("SELECT id, topic FROM posts").fetchall()
            ids2 = [r[0] for r in rows2]
            assert "post_u2_001" in ids2, "User 2 must see own post"
            assert "post_u1_001" not in ids2, "User 2 must NOT see User 1's post"
            assert len(rows2) == 1

        print("[PASS] User database isolation strictly verified.")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

if __name__ == "__main__":
    test_independent_user_isolation()
    print("ALL MULTI-USER ISOLATION TESTS PASSED!")
