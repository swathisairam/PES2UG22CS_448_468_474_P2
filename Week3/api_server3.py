
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import subprocess
import uuid
import threading
import time

app = Flask(__name__)

# Store node info and pod info
nodes = {}      # {node_id: {"cpu_cores": int, "status": "active", "pods": [], "last_heartbeat": timestamp}}
pods = {}       # {pod_id: {"cpu_required": int, "node_id": str}}

HEARTBEAT_TIMEOUT = 15  # seconds

@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.json
    if "cpu_cores" not in data:
        return jsonify({"error": "Missing CPU cores"}), 400

    node_id = str(uuid.uuid4())[:8]
    cpu_cores = data["cpu_cores"]
    container_name = f"node_{node_id}"

    # Launch Docker container (optional - comment out if testing without Docker)
    subprocess.run(["docker", "run", "-d", "--name", container_name, "ubuntu", "sleep", "infinity"])

    nodes[node_id] = {
        "cpu_cores": cpu_cores,
        "status": "active",
        "pods": [],
        "last_heartbeat": datetime.utcnow()
    }

    return jsonify({"message": "Node added", "node_id": node_id}), 201

@app.route('/launch_pod', methods=['POST'])
def launch_pod():
    data = request.json
    if "cpu" not in data:
        return jsonify({"error": "Missing CPU requirement"}), 400

    cpu_needed = data["cpu"]
    pod_id = str(uuid.uuid4())[:8]

    # First-Fit Scheduling
    for node_id, node in nodes.items():
        if node["status"] == "active" and node["cpu_cores"] >= cpu_needed:
            node["cpu_cores"] -= cpu_needed
            node["pods"].append(pod_id)
            pods[pod_id] = {
                "cpu_required": cpu_needed,
                "node_id": node_id
            }
            return jsonify({"message": f"Pod {pod_id} scheduled", "node_id": node_id}), 201

    return jsonify({"error": "No available node"}), 400

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    node_id = data.get("node_id")
    if node_id not in nodes:
        return jsonify({"error": "Unknown node"}), 404

    nodes[node_id]["last_heartbeat"] = datetime.utcnow()
    nodes[node_id]["status"] = "active"
    return jsonify({"message": "Heartbeat received"}), 200


@app.route('/list_nodes', methods=['GET'])
def list_nodes():
    node_list = []
    for node_id, node in nodes.items():
        node_list.append({
            "node_id": node_id,
            "cpu_cores": node["cpu_cores"],
            "pods": node["pods"],
            "status": node["status"]
        })
    return jsonify({"nodes": node_list})


@app.route('/list_pods', methods=['GET'])
def list_pods():
    return jsonify(pods)

# Background thread to monitor heartbeat status
def monitor_nodes():
    while True:
        now = datetime.utcnow()
        for node_id, node in nodes.items():
            if (now - node["last_heartbeat"]) > timedelta(seconds=HEARTBEAT_TIMEOUT):
                node["status"] = "inactive"
        time.sleep(5)

# Start the monitor thread
threading.Thread(target=monitor_nodes, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
