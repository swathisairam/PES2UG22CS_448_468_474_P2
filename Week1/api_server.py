from flask import Flask, request, jsonify
import subprocess
import uuid

app = Flask(__name__)

# Store nodes in a dictionary {node_id: {"cpu_cores": int, "status": "active"}}
nodes = {}

@app.route('/add_node', methods=['POST'])
def add_node():
    data = request.json
    if "cpu_cores" not in data:
        return jsonify({"error": "Missing CPU cores"}), 400
    
    node_id = str(uuid.uuid4())[:8]  # Generate unique node ID
    cpu_cores = data["cpu_cores"]

    # Launch a new container simulating a node
    container_name = f"node_{node_id}"
    subprocess.run(["docker", "run", "-d", "--name", container_name, "ubuntu", "sleep", "infinity"])

    # Store node details
    nodes[node_id] = {"cpu_cores": cpu_cores, "status": "active"}

    return jsonify({"message": "Node added", "node_id": node_id}), 201

@app.route('/list_nodes', methods=['GET'])
def list_nodes():
    return jsonify(nodes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
