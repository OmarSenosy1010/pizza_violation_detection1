"""
streaming_service.py
Streams violation and non-violation frames to frontend in real-time using FastAPI + WebSocket.
"""
import asyncio
import base64
import json
import pika
import numpy as np
import sqlite3
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# ===== Static Files (frontend) =====
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# ===== SQLite Violation Count =====
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "violations.db")

@app.get("/violations/count")
async def get_violation_count():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM violations")
        count = cursor.fetchone()[0]
        conn.close()
        return {"violations": count}
    except Exception as e:
        return {"violations": 0, "error": str(e)}

# ===== WebSocket for Real-Time Stream =====
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
DETECT_QUEUE = "annotated_frames"

def get_rabbitmq_connection():
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        return pika.BlockingConnection(params)
    except Exception as e:
        print(f"Error connecting to RabbitMQ: {e}")
        return None

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("✅ WebSocket connected")
    
    conn_r = get_rabbitmq_connection()
    if not conn_r:
        await ws.close()
        return
    
    ch = conn_r.channel()
    ch.queue_declare(queue=DETECT_QUEUE, durable=True)

    try:
        last_sent = time.time()
        while True:
            try:
                method_frame, header_frame, body = ch.basic_get(queue=DETECT_QUEUE, auto_ack=True)
                if body:
                    data = json.loads(body)
                    img_b64 = data["image"]
                    violation = data.get("violation", False)

                    message = {
                        "image": img_b64,
                        "violation": violation,
                        "timestamp": time.time()
                    }

                    await ws.send_text(json.dumps(message))
                    print("Frame sent at", time.time())
                    last_sent = time.time()
                else:
                    # Send heartbeat every 1s if no frame
                    if time.time() - last_sent > 1:
                        await ws.send_text(json.dumps({"heartbeat": True}))
                        last_sent = time.time()
                    await asyncio.sleep(0.01)
            except WebSocketDisconnect:
                print("❌ WebSocket disconnected")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(0.05)
    finally:
        try:
            conn_r.close()
            await ws.close()
        except:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
