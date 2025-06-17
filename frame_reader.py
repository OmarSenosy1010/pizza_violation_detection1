"""
frame_reader.py
Reads frames from a video file and publishes them to a RabbitMQ queue for downstream processing.
"""
import cv2
import pika
import base64
import json

# RabbitMQ connection parameters
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
VIDEO_PATH    = "videos\Sah_w_b3dha_ghalt.mp4" 
QUEUE_NAME    = "frames"

# Establish connection to RabbitMQ
params   = pika.URLParameters(RABBITMQ_URL)
conn     = pika.BlockingConnection(params)
channel  = conn.channel()
channel.queue_declare(queue=QUEUE_NAME, durable=True)

# Open video file
cap = cv2.VideoCapture(VIDEO_PATH)
frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break  # End of video

    # Encode frame as JPEG and then to base64
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_b64  = base64.b64encode(buffer).decode('utf-8')

    # Prepare message
    msg = {"frame_id": frame_id, "image": jpg_b64}
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(msg),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(f"[FrameReader] Sent frame {frame_id}")
    frame_id += 1

# Release resources
cap.release()
conn.close()
