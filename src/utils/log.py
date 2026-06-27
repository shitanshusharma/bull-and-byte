"""Tiny stdout logger used across the package."""


def log(msg):
    print(f"[bull-and-byte] {msg}", flush=True)
