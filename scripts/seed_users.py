import bcrypt
from backend.database import get_db_connection

def seed_users():
    print("Seeding test users...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Admin User
    admin_user = ("test_admin", "admin@test.com", bcrypt.hashpw(b"AdminPass456!", bcrypt.gensalt()).decode())
    # 2. Analyst User
    analyst_user = ("test_analyst", "analyst@test.com", bcrypt.hashpw(b"SecurePass123!", bcrypt.gensalt()).decode())
    
    users = [admin_user, analyst_user]
    
    for username, email, password_hash in users:
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            user_id = cursor.lastrowid
            
            # Assign role
            role_name = "admin" if username == "test_admin" else "analyst"
            cursor.execute(
                "INSERT INTO user_roles (user_id, role_id) SELECT %s, id FROM roles WHERE role_name = %s",
                (user_id, role_name)
            )
            print(f"  ✅ User '{username}' created with role '{role_name}'.")
        except Exception as e:
            print(f"  ⏭️ User '{username}' already exists or failed: {e}")
            
    conn.commit()
    cursor.close()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_users()
