import os

def ensure_dirs():
    os.makedirs("raw", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    os.makedirs("finished", exist_ok=True)
