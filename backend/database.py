"""

File: backend/database.py

Responsibility: Defines the MySQL database schema and provides
a helper function to get a database connection.

The schema covers:
  - users       : Stores registered users with hashed passwords.
  - roles       : Defines user roles (admin, analyst, general_user).
  - user_roles  : Many-to-many link between users and roles.
  - documents   : Metadata for every PDF uploaded into the system.

VIVA NOTE: This is the RBAC (Role-Based Access Control) layer. Before
ANY vector search happens, we check this DB to confirm the user has
access. O(1) lookup using indexed user_id prevents unauthorized access.
"""

import os
import mysql.connector
from mysql.connector import connection
from dotenv import load_dotenv

# Load environment variables from the .env file (never hard-code credentials)
load_dotenv()


# ── Database Connection ────────────────────────────────────────────────────────
def get_db_connection(use_database=True) -> connection.MySQLConnection:
    """
    Returns a new MySQL connection using environment variables.
    Handles connection errors gracefully.
    """
    try:
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 3306)),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
        }
        if use_database:
            config["database"] = os.getenv("DB_NAME", "policy_retrieval_db")
            
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        if err.errno == 1045:
            raise Exception("MySQL Access Denied: Please check your DB_PASSWORD in the .env file.")
        elif err.errno == 1049:
            # If database doesn't exist, we might be calling this from init_database
            if use_database:
                raise Exception(f"MySQL Database '{os.getenv('DB_NAME')}' not found. Please run 'python backend/database.py' to initialize.")
        raise err


# ── Schema SQL ─────────────────────────────────────────────────────────────────
# Run this SQL to initialize the database on first setup.
SCHEMA_SQL = """
-- Create the database if it doesn't already exist
CREATE DATABASE IF NOT EXISTS policy_retrieval_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE policy_retrieval_db;

-- roles: Defines what a user can do in the system
CREATE TABLE IF NOT EXISTS roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    role_name   VARCHAR(50) NOT NULL UNIQUE,  -- 'admin', 'analyst', 'general_user'
    description VARCHAR(255),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- users: Stores user credentials (passwords are bcrypt-hashed, never plain text)
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,       -- bcrypt hash of the password
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Index on email for O(1) lookup during authentication
    INDEX idx_email (email)
);

-- user_roles: Many-to-many link (one user can have multiple roles)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id     INT NOT NULL,
    role_id     INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- documents: Every PDF uploaded is tracked here for RBAC filtering
CREATE TABLE IF NOT EXISTS documents (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    session_id    INT DEFAULT NULL,             -- Optional: Link to a specific chat session for isolation
    filename      VARCHAR(255) NOT NULL UNIQUE, -- Exact filename as stored in raw_pdfs/
    display_name  VARCHAR(255),                 -- Human-readable name shown in UI
    description   TEXT,
    access_level  ENUM('public', 'analyst_only', 'admin_only') DEFAULT 'public',
    uploaded_by   INT,                          -- FK to the admin user who uploaded this
    uploaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    -- Index on filename for fast O(log n) lookup during citation filtering
    INDEX idx_filename (filename),
    INDEX idx_session (session_id)
);

-- Seed the default roles
INSERT IGNORE INTO roles (role_name, description) VALUES
    ('admin',        'Can upload documents, manage users, and access all policies.'),
    ('analyst',      'Can search and analyze all policy documents.'),
    ('general_user', 'Can only query publicly accessible policy documents.');

-- chat_sessions: Tracks independent conversation threads for each user
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    title       VARCHAR(255) DEFAULT 'New Conversation',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- chat_messages: Stores every message within a conversation (survives refreshes)
CREATE TABLE IF NOT EXISTS chat_messages (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    session_id  INT NOT NULL,
    role        ENUM('user', 'bot') NOT NULL,
    content     TEXT NOT NULL,
    citations   JSON,  -- Stores citation data (document name, page, etc) for bot responses
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);
"""


def init_database():
    """
    Runs the schema SQL to create all tables and seed default roles.
    Safe to call multiple times — uses CREATE IF NOT EXISTS / INSERT IGNORE.
    """
    print("Initialising database schema...")
    # Connect without specifying a database to ensure we can create it
    conn = get_db_connection(use_database=False)
    cursor = conn.cursor()
    
    # Execute each statement individually
    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as err:
                # Ignore "Database already exists" type warnings if needed
                print(f"  Info: {err}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialised successfully.")


if __name__ == "__main__":
    init_database()
