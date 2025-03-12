from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import subprocess
import json
import re
import os
import sys
sys.path.append(r'C:\Users\Prashanth Babu\Documents\klayschool\klayschool\python_server\venv\Lib\site-packages')
print("Current working directory:", os.getcwd())
import logging
import base64
from datetime import datetime
from pyzbar.pyzbar import decode
from PIL import Image
import io
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
#CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes
#socketio = SocketIO(app, cors_allowed_origins="*")  # Enable CORS for frontend
# socketio = SocketIO(app, cors_allowed_origins=["http://192.168.0.113:3000"])

CORS(app, resources={r"/*": {"origins": ["http://192.168.0.113:3000", "http://localhost:3000"]}})
socketio = SocketIO(app, cors_allowed_origins=["http://192.168.0.113:3000", "http://localhost:3000"])



otcard_peer = None  # Store OTCard peer's session ID
ot_status = {}  # Dictionary to maintain OT status data (e.g., {"1": {...}, "2": {...}})
# Dictionary to store connected OTCard clients by OT ID
otcard_peers = {}  # Example: {"1": ["sid1", "sid2"], "2": ["sid3"]}

@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on("register-otcard-peer")
def register_otcard(data):
    ot_id = str(data.get("otId"))  # Convert to string for consistency
    if not ot_id:
        print("No OT ID provided")
        return
    # Add the client's session ID to the correct OT room
    join_room(ot_id)
    if ot_id not in otcard_peers:
        otcard_peers[ot_id] = []

    otcard_peers[ot_id].append(request.sid)
    print(f"OTCard {ot_id} Registered: {otcard_peers[ot_id]}")
    print(f"OTCard status details on register otcard: {ot_status}")

    # Send all stored OT status data if available
    if ot_id in ot_status and ot_status[ot_id]:
        print(f"Sending stored OT data to OT-{ot_id}: {ot_status[ot_id]}")
        for stored_data in ot_status[ot_id]:
            emit("receive-otstatus-data", stored_data, room=request.sid)  # Send to newly connected OT client

@socketio.on("push-data")
def handle_push_data(data):
    print(f"data value: {data}")
    ot_id = str(data.get("otId"))  # Extract OT ID from pushed data
    if not ot_id or ot_id not in otcard_peers:
        print(f"No OTCard clients registered for OT-{ot_id}")
        return
    # Ensure ot_status for the given ot_id is a list
    if ot_id not in ot_status:
        ot_status[ot_id] = []
    # Append the new data to the list
    ot_status[ot_id].append(data)
    print(f"OTCard status details: {ot_status}")
    # If there are registered OT clients, send the data
    if ot_id in otcard_peers and otcard_peers[ot_id]:
        print(f"Sending data to OT-{ot_id}: {data}")
        emit("receive-data", data, room=ot_id)
    else:
        print(f"No OT clients registered for OT-{ot_id}. Data stored for later.")

@socketio.on("disconnect")
def handle_disconnect():
    for ot_id, clients in otcard_peers.items():
        if request.sid in clients:
            clients.remove(request.sid)
            leave_room(ot_id)
            print(f"Client {request.sid} removed from OT-{ot_id}")
            if not clients:  # If no clients left in the room, remove the OT ID
                del otcard_peers[ot_id]
            break
    print(f"Client disconnected: {request.sid}")      

@app.route('/otfeed', methods=['POST'])
def upload_frame():
    try:
        data = request.get_json()

        # Extract frame and camera ID
        frame_data = data.get('frame', None)
        camera_id = data.get('cameraId', 'unknown')

        if not frame_data:
            return jsonify({'error': 'No frame data provided'}), 400

        # Decode base64 frame
        frame_data = frame_data.split(',')[1]  # Remove the "data:image/jpeg;base64," prefix
        frame_bytes = base64.b64decode(frame_data)

        # Generate a unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        # Load the frame as a PIL image
        image = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        image_np = np.array(image)  # Convert to NumPy array for QR code detection
        # Detect QR codes in the frame
        qr_codes = decode(image_np)
        qr_data_list = []

        for qr in qr_codes:
            qr_data_list.append(qr.data.decode('utf-8'))  # Decode and collect QR code data

        print(f'Frame saved: {qr_data_list}')
        return jsonify({'message': 'Frame received successfully', 'path': qr_data_list}), 200
    except Exception as e:
        print(f'Error: {e}')
        return jsonify({'error': str(e)}), 500        
    
@app.route('/api/wheel_in_out', methods=['POST'])
def wheel_in_out():
    try:
        print('inside wheelin method')
        socketio.emit('wheelinoutdata', 'Received from server', room=request.sid)
        return jsonify({"message": "Wheel in  received"}), 200
    except Exception as e:
        return jsonify({"error": "Wheel in check", "details": str(e)}), 500
    
@app.route('/api/qr_details', methods=['POST'])
def qr_details():
    try:
        print('inside qr_details method')
        return jsonify({"message": "Qr details received"}), 200
    except Exception as e:
        return jsonify({"error": "qr details", "details": str(e)}), 500

@app.route('/api/usage_count', methods=['POST'])
def usage_count():
    try:
        print('inside usage_count method')
        return jsonify({"message": "Usage count received"}), 200
    except Exception as e:
        return jsonify({"error": "usage count", "details": str(e)}), 500        

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
