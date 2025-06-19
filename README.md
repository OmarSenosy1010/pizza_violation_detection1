
# pizza_violation_detection1

# Pizza Violation Detection System

This project detects and logs violations in a pizza preparation environment using computer vision (YOLO), message queues (RabbitMQ), and a real-time web dashboard. It tracks whether a scooper is used when handling pizza and logs violations with images and timestamps.

## Features

- **Real-time detection** of hand, scooper, and pizza using YOLO.
- **Violation logging** with images and timestamps in SQLite.
- **Live dashboard** to monitor violations and view the latest violation frame.
- **Modular microservices** using Python, FastAPI, and RabbitMQ.

## Architecture

![Architecture Diagram](architecture_diagram.jpg)

### Architecture Diagram Component Descriptions

- **Frame Reader:** Reads frames from a video file and publishes each frame as a message to the `frames` queue in RabbitMQ. This decouples video reading from detection and allows for scalable, asynchronous processing.
- **RabbitMQ (Frames Queue):** Acts as a message broker. The `frames` queue temporarily stores video frames published by the Frame Reader until they are consumed by the Detection Service. Ensures reliable, decoupled communication.
- **Detection Service:** Consumes frames from the `frames` queue, runs YOLO-based object detection to identify hands, scoopers, and pizza, and applies the violation detection logic. If a violation is detected, it publishes the annotated frame to the `detected_frames` queue in RabbitMQ.
- **RabbitMQ (Detected Frames Queue):** Another message queue in RabbitMQ. Stores frames where violations have been detected, making them available for both storage and real-time streaming.
- **Storage Service:** Consumes violation frames from the `detected_frames` queue, saves the images to disk, and logs metadata (frame ID, timestamp, image path) to an SQLite database for record-keeping and later review.
- **SQLite DB:** A lightweight, file-based database that stores metadata about each violation (such as frame ID, timestamp, and image path). Enables querying and reporting of historical violations.
- **Streaming Service:** Consumes violation frames from the `detected_frames` queue and serves them in real-time to the frontend via a WebSocket API. This enables live monitoring of violations as they occur.
- **Frontend:** A web-based dashboard that connects to the Streaming Service via WebSocket. Displays the latest violation frame in real-time and shows the total number of violations, providing an intuitive interface for monitoring.

## Violation Detection Logic

The system uses a state machine to track each detected hand and determine if a violation occurs:

1. **Idle State:**  
   - Each detected hand starts in the "idle" state.
   - If a hand enters a Region of Interest (ROI), its state changes to "in_roi".

2. **In ROI State:**  
   - While in the ROI, the system checks if a "scooper" is detected near the hand.
   - If a scooper is seen close to the hand, a flag (`scooper_seen`) is set to `True`.

3. **Pizza Area Check:**  
   - If the hand moves from the ROI to the pizza area (detected as a bounding box labeled "pizza"), the system checks:
     - If `scooper_seen` is `False`, a violation is recorded (the hand touched the pizza without using a scooper).
     - The hand's state resets to "idle".

4. **Tracker Management:**  
   - Hands that disappear for a certain number of frames are removed from tracking.

This logic ensures that only hands that enter the ROI and then touch the pizza without using a scooper are flagged as violations.

![Violation Detection Logic](violation_detection_logic.jpg)

## Prerequisites

- Python 3.8+
- [RabbitMQ](https://www.rabbitmq.com/download.html) server running locally (default: `amqp://guest:guest@localhost:5672/`)
- A video file for ROI selection and frame reading (default: `videos/Sah_w_b3dha_ghalt.mp4`)
- YOLO model weights file (`yolo12m-v2.pt` provided)

## Installation

1. **Clone the repository** and navigate to the project directory.

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start RabbitMQ** (if not already running):
   - On Windows: Use the RabbitMQ Service or run `rabbitmq-server.bat` from the installation directory.
   - On Linux/macOS: Run `rabbitmq-server` in a terminal.

4. **Prepare your video file:**
   - Place your video at `videos/Sah_w_b3dha_ghalt.mp4` or update the path in `frame_reader.py` and `detection_service/roi_selector.py`.

## Usage

### 1. Start the Frame Reader

Open a terminal and run:
```bash
cd ../pizza_violation_detection1
python frame_reader.py
```
- This script reads frames from the video and publishes them to RabbitMQ.

### 2. Select Regions of Interest (ROIs) and Start Detection/Storage Services

Open a new terminal and run:
```bash
cd ../pizza_violation_detection1/detection_service
python run_all.py
```
- preferred to run (run_all.py) from VScode
- Use the mouse to select multiple ROIs, then press ENTER or SPACE to confirm, and Exit.
- The selected ROIs will be saved to config.json.
- Then launch both the detection and storage services in separate windows.

### 3. Start the Streaming (WebSocket) Service

Open another terminal and run:
```bash
cd ../pizza_violation_detection1
python streaming_service.py
```
- This starts a FastAPI server at `[ws://localhost:8000/](http://127.0.0.1:8000)` for real-time frame streaming.

### 4. Open the Frontend Dashboard

Open `frontend/index.html` in your web browser.  
- The dashboard will show the total number of violations and display the latest violation frame in real time.

> **Note:** For full functionality, you may need to serve the frontend via a local web server (e.g., `python -m http.server` in the `frontend` directory) if your browser blocks WebSocket or fetch requests from `file://` URLs.

## Data Storage

- **Violation images** are saved in `db\violations`.
- **Violation logs** are stored in `db\violations.db` (SQLite).

## Customization

- **YOLO Model:** Replace `yolo12m-v2.pt` with your own YOLO weights if needed.
- **Video Source:** Update the video path in `frame_reader.py` and `roi_selector.py` as required.

## Troubleshooting

- Ensure RabbitMQ is running and accessible at the default URL.
- If you encounter issues with OpenCV windows, ensure you have a display environment (not headless).
- For WebSocket or fetch errors in the frontend, use a local web server.

## License

This project is for educational and research purposes. 
 ea1f9df (first commit)
