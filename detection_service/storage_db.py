"""
storage_db.py
Consumes detected violation frames from RabbitMQ, saves images to disk, and logs metadata to an SQLite database.
"""
import os
import sqlite3
import pika
import base64
import json
from datetime import datetime

# (SQLite)
DB_DIR  = "db"
DB_PATH = os.path.join(DB_DIR, "violations.db")
os.makedirs(DB_DIR, exist_ok=True)

# Connect to SQLite database
conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
  CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id INTEGER,
    timestamp DATETIME,
    image_path TEXT
  )
""")
conn.commit()

# RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
DETECT_QUEUE = "detected_frames"

params = pika.URLParameters(RABBITMQ_URL)
conn_r = pika.BlockingConnection(params)
ch     = conn_r.channel()
ch.queue_declare(queue=DETECT_QUEUE, durable=True)

OUT_DIR = os.path.join(DB_DIR, "violations")
os.makedirs(OUT_DIR, exist_ok=True)

def callback(ch, method, properties, body):
    """
    Callback function to process detected violation frames from RabbitMQ.
    Decodes the image, saves it to disk, and logs the event in the database.
    """
    data     = json.loads(body)
    frame_id = data["frame_id"]
    img_b64  = data["image"]

    # Decode image from base64
    img_data = base64.b64decode(img_b64)
    # Save image to disk
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"frame_{frame_id}_{timestamp}.jpg"
    path      = os.path.join(OUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(img_data)

    # Log event in SQLite database
    cursor.execute(
      "INSERT INTO violations(frame_id, timestamp, image_path) VALUES (?,?,?)",
      (frame_id, datetime.now(), path)
    )
    conn.commit()

    print(f"[Storage] Saved violation #{cursor.lastrowid} → {filename}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

ch.basic_qos(prefetch_count=1)
ch.basic_consume(queue=DETECT_QUEUE, on_message_callback=callback)

print("[Storage] Waiting for detected frames...")
ch.start_consuming()
