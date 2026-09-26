import asyncio
import database
from datetime import datetime, timezone

async def session_expiry():
    while True:
        try:
            now = datetime.now(timezone.utc)

            collections = [
                database.comprehension_sessions_col,
                database.essay_sessions_col,
                database.speaking_sessions_col,
                database.listening_sessions_col
            ]

            for col in collections:
                if col is not None:
                    col.update_many(
                        {
                            "expires_at": {"$lt": now},
                            "status": "in_progress"
                        },
                        {"$set": {"status": "expired"}}
                    )

            print("🧹 Expired sessions cleaned")

        except Exception as e:
            print("❌ Expiry job error:", e)

        await asyncio.sleep(300)