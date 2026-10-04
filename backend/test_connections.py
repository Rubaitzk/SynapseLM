import os
import psycopg2
import redis
from dotenv import load_dotenv

load_dotenv()

def test_postgres():
    url = os.getenv("DATABASE_URL")
    print(f"Connecting to Postgres: {url}")
    conn = psycopg2.connect(url)
    conn.close()
    print("Postgres connection OK")

def test_redis():
    url = os.getenv("REDIS_URL")
    print(f"Connecting to Redis: {url}")
    r = redis.from_url(url)
    r.ping()
    print("Redis connection OK")

if __name__ == "__main__":
    test_postgres()
    test_redis()
