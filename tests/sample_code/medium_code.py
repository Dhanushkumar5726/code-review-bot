
import json

def read_config(filepath):
    f = open(filepath)
    content = f.read()
    config = json.loads(content)
    return config

def get_host(config):
    return config["database"]["host"]

def connect(filepath):
    try:
        config = read_config(filepath)
        host = get_host(config)
        print(f"Connecting to {host}")
    except:
        print("Something went wrong")
