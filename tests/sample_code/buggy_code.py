
import pickle

password = "admin123"

def get_user(username):
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return db.execute(query)

def load_data(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)

def divide(a, b):
    return a / b
