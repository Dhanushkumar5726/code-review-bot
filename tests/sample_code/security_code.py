
import sqlite3
import os

SECRET_KEY = "hardcoded-secret-key-12345"
DB_PASSWORD = "admin@123"

def search_users(keyword):
    query = "SELECT * FROM users WHERE name LIKE '%" + keyword + "%'"
    conn = sqlite3.connect("users.db")
    return conn.execute(query).fetchall()

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    conn = sqlite3.connect("users.db")
    return conn.execute(query).fetchone()
