"""
Script to wipe transactional data from the MySQL database.
Preserves: users, roles, user_roles (schema intact)
Clears: chat_messages, chat_sessions, documents
"""

import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "policy_retrieval_db"),
)
cursor = conn.cursor()

# Disable FK checks temporarily so we can truncate in any order
cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

tables = ["chat_messages", "chat_sessions", "documents"]
for table in tables:
    cursor.execute(f"TRUNCATE TABLE `{table}`;")
    print(f"  [OK] Cleared: {table}")

cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
conn.commit()
cursor.close()
conn.close()

print("\nMySQL cleanup complete. Users and roles have been preserved.")
