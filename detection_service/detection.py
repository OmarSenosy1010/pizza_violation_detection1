"""
detection.py
Consumes frames from RabbitMQ, detects hands/scoopers/pizza using YOLO, tracks hands,
publishes all annotated frames to 'annotated_frames'، and only violation frames
to 'detected_frames' .
"""
import cv2
import pika
import base64
import json
import numpy as np
from ultralytics import YOLO

# RabbitMQ connection and config
RABBITMQ_URL   = "amqp://guest:guest@localhost:5672/"
FRAME_QUEUE    = "frames"
ANNOT_QUEUE    = "annotated_frames"  
DETECT_QUEUE   = "detected_frames"   
CONFIG_PATH    = "C:/Users/Omar/Desktop/pizza_violation_detection1/config.json"

# Load ROIs from config.json
with open(CONFIG_PATH) as f:
    cfg = json.load(f)
roi_list = cfg["rois"]  # [[x, y, w, h], ...]

# Load YOLO model
model = YOLO("C:/Users/Omar/Desktop/pizza_violation_detection1/yolo12m-v2.pt")

# Setup RabbitMQ
params = pika.URLParameters(RABBITMQ_URL)
conn   = pika.BlockingConnection(params)
ch     = conn.channel()

ch.queue_declare(queue=FRAME_QUEUE,    durable=True)
ch.queue_declare(queue=ANNOT_QUEUE,    durable=True)
ch.queue_declare(queue=DETECT_QUEUE,   durable=True)

# Trackers: id -> {centroid, state, scooper_seen, disappear}
trackers    = {}
next_id     = 1
MAX_DISAPPEAR = 30  # Max frames before tracker is removed

def register(centroid):
    global next_id
    trackers[next_id] = {
        "centroid": centroid,
        "state": "idle",
        "scooper_seen": False,
        "disappear": 0
    }
    next_id += 1

def deregister(tid):
    if tid in trackers:
        del trackers[tid]

def update_trackers(detections):
    global trackers
    if not detections:
        # Increase disappear count
        to_del = []
        for tid, tr in trackers.items():
            tr["disappear"] += 1
            if tr["disappear"] > MAX_DISAPPEAR:
                to_del.append(tid)
        for tid in to_del:
            deregister(tid)
        return

    # If no existing trackers, register all detections
    if not trackers:
        for c in detections:
            register(c)
        return

    tids      = list(trackers.keys())
    centroids = [trackers[tid]["centroid"] for tid in tids]

    # Compute distance matrix and match
    D = np.linalg.norm(
        np.array(centroids)[:, None, :] - np.array(detections)[None, :, :],
        axis=2
    )
    rows = D.min(axis=1).argsort()
    cols = D.argmin(axis=1)[rows]

    used_rows = set()
    used_cols = set()
    for r, c in zip(rows, cols):
        if r in used_rows or c in used_cols:
            continue
        tid = tids[r]
        trackers[tid]["centroid"]  = detections[c]
        trackers[tid]["disappear"] = 0
        used_rows.add(r)
        used_cols.add(c)

    # Register new detections
    for i, c in enumerate(detections):
        if i not in used_cols:
            register(c)
    # Deregister lost trackers
    for i, tid in enumerate(tids):
        if i not in used_rows:
            trackers[tid]["disappear"] += 1
            if trackers[tid]["disappear"] > MAX_DISAPPEAR:
                deregister(tid)

def callback(ch, method, properties, body):
    data     = json.loads(body)
    frame_id = data["frame_id"]
    img_b64  = data["image"]

    # Decode image
    img_bytes = base64.b64decode(img_b64)
    nparr     = np.frombuffer(img_bytes, dtype=np.uint8)
    frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Run YOLO
    results = model(frame)[0]

    # Draw ROIs
    for x, y, w, h in roi_list:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    hands = []
    scoopers = []
    pizza_boxes = []

    # Parse detections
    for box in results.boxes:
        cls      = results.names[int(box.cls[0])]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy  = (x1 + x2)//2, (y1 + y2)//2

        if cls == "hand":
            hands.append((cx, cy))
            color = (0, 0, 255)
        elif cls == "scooper":
            scoopers.append((cx, cy))
            color = (0, 255, 0)
        elif cls == "pizza":
            pizza_boxes.append((x1, y1, x2, y2))
            color = (0, 255, 255)
        else:
            color = (200, 200, 200)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, cls, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Update trackers with new hands
    update_trackers(hands)

    # Violation detection
    violation = False
    for tr in trackers.values():
        cx, cy = tr["centroid"]
        if tr["state"] == "idle":
            # hand enters ROI
            if any(x < cx < x+w and y < cy < y+h for x, y, w, h in roi_list):
                tr["state"] = "in_roi"
                tr["scooper_seen"] = False
        elif tr["state"] == "in_roi":
            # check scooper
            if any(x < cx < x+w and y < cy < y+h for x, y, w, h in roi_list) and \
               any(abs(cx - sx) < 20 and abs(cy - sy) < 20 for sx, sy in scoopers):
                tr["scooper_seen"] = True
            # check pizza
            for px1, py1, px2, py2 in pizza_boxes:
                if px1 < cx < px2 and py1 < cy < py2:
                    if not tr["scooper_seen"]:
                        violation = True
                    tr["state"] = "idle"

    # Encode annotated frame
    _, buf       = cv2.imencode('.jpg', frame)
    img_annot    = base64.b64encode(buf).decode('utf-8')
    msg_annot    = {
        "frame_id":  frame_id,
        "image":     img_annot,
        "violation": violation
    }

    # 1️⃣ Publish every annotated frame
    ch.basic_publish(
        exchange='',
        routing_key=ANNOT_QUEUE,
        body=json.dumps(msg_annot),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    # 2️⃣ Publish only violation frames to detected_frames
    if violation:
        ch.basic_publish(
            exchange='',
            routing_key=DETECT_QUEUE,
            body=json.dumps(msg_annot),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"🚨 Violation at frame {frame_id}")
    else:
        print(f"[OK] Frame {frame_id}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start consuming
ch.basic_qos(prefetch_count=1)
ch.basic_consume(queue=FRAME_QUEUE, on_message_callback=callback)
print("[Detection] Waiting for frames…")
ch.start_consuming()
