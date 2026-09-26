from pymongo import MongoClient
import os
import time
from dotenv import load_dotenv
import threading
import certifi

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = None
db = None
connected = False

users_col = None

essay_sessions_col = None
essay_results_col = None

comprehension_sessions_col = None
comprehension_results_col = None

speaking_sessions_col = None
speaking_results_col = None

listening_sessions_col = None
listening_results_col = None

user_results_col = None


def connect_mongo():
    global client, db, connected
    global users_col
    global essay_sessions_col, essay_results_col
    global comprehension_sessions_col, comprehension_results_col
    global speaking_sessions_col, speaking_results_col
    global listening_sessions_col, listening_results_col
    global user_results_col

    if connected:
        return

    max_retries = 10
    attempt = 0
    connected = False

    while not connected and attempt < max_retries:
        try:
            attempt += 1
            print(f"⏳ Trying to connect to MongoDB... (Attempt {attempt}/{max_retries})")

            client = MongoClient(
                MONGO_URI,
                tls=True,
                tlsCAFile=certifi.where(),
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                retryWrites=True
            )

            client.admin.command("ping")

            db = client["studentDB"]
            connected = True

            print("✅ MongoDB connected successfully")

            # collections
            essay_sessions_col = db["essay_sessions"]
            essay_results_col = db["essay_results"]

            comprehension_sessions_col = db["comprehension_sessions"]
            comprehension_results_col = db["comprehension_results"]

            speaking_sessions_col = db["speaking_sessions"]
            speaking_results_col = db["speaking_results"]

            listening_sessions_col = db["listening_sessions"]
            listening_results_col = db["listening_results"]

            users_col = db["users"]
            user_results_col = db["user_results"]

            # indexes for fast lookup
            users_col.create_index("email", unique=True)

            essay_sessions_col.create_index("session_id", unique=True)
            essay_sessions_col.create_index("expires_at")
            essay_sessions_col.create_index("status")
            essay_results_col.create_index("user_id")
            essay_results_col.create_index("session_id")

            comprehension_sessions_col.create_index("session_id", unique=True)
            comprehension_sessions_col.create_index("expires_at")
            comprehension_sessions_col.create_index("status")
            comprehension_results_col.create_index("user_id")
            comprehension_results_col.create_index("session_id")

            speaking_sessions_col.create_index("session_id", unique=True)
            speaking_sessions_col.create_index("expires_at")
            speaking_sessions_col.create_index("status")
            speaking_results_col.create_index("user_id")
            speaking_results_col.create_index("session_id")

            listening_sessions_col.create_index("session_id", unique=True)
            listening_sessions_col.create_index("expires_at")
            listening_sessions_col.create_index("status")
            listening_results_col.create_index("user_id")
            listening_results_col.create_index("session_id")

            user_results_col.create_index("user_id", unique=True)

        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")

            if attempt < max_retries:
                print("🔁 Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("💀 Max retries reached. Stopping MongoDB connection attempts.")
                raise RuntimeError("MongoDB connection failed after maximum retries")


def start_db():
    threading.Thread(target=connect_mongo, daemon=True).start()