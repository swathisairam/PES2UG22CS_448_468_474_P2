from flask import Flask, request, jsonify
import uuid
import docker
import threading
import time
import logging
import os
import json
import argparse
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Kubernetes-like Cluster Simulation API Server')
parser.add_argument('--port', type=int, default=5001, help='Port to run the server on (default: 5001)')
args = parser.parse_args()

app = Flask(__name__)

# Initialize Docker client - make it global
docker_client = None

try:
    # Try to connect using the default Docker socket
    docker_client = docker.from_env()
    logger.info("Successfully connected to Docker")
except docker.errors.DockerException as e:
    # If on macOS, try to connect using the Docker Desktop socket
    import platform
    if platform.system() == "Darwin":  # Darwin is macOS
        os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
        # Alternative socket paths to try if the above doesn't work
        potential_paths = [
            "unix:///var/run/docker.sock",
            "unix://~/Library/Containers/com.docker.docker/Data/docker.sock",
            "unix://~/.docker/run/docker.sock"
        ]
        
        connected = False
        for path in potential_paths:
            try:
                os.environ["DOCKER_HOST"] = path
                docker_client = docker.from_env()
                logger.info(f"Successfully connected to Docker using: {path}")
                connected = True
                break
            except Exception:
                continue
                
        if not connected:
            logger.warning("Could not connect to Docker. Please ensure Docker Desktop is running.")
            logger.info("Running in simulation mode without actual Docker containers.")
            docker_client = None
    else:
        # On other systems, propagate the error
        logger.error(f"Docker connection error: {str(e)}")
        docker_client = None

class NodeManager:
    def __init__(self):
        self.nodes = {}  # Dictionary to store node information {node_id: {cpu_cores, status, pods, container_id}}
        self.node_last_heartbeat = {}  # Track last heartbeat time for each node
        # Store reference to global docker_client
        global docker_client
        self.docker_client = docker_client
        # Track the last node used for round-robin scheduling
        self.last_used_node_index = -1

    def add_node(self, cpu_cores):
        """Add a new node to the cluster with specified CPU cores"""
        node_id = str(uuid.uuid4())
    
        # Check if Docker is available - use self.docker_client instead of docker_client
        if self.docker_client is not None:
            # Launch a Docker container to simulate the node
            try:
                container = self.docker_client.containers.run(
                    "python:3.9-slim",
                    f"python /app/node.py {node_id} {cpu_cores}",
                    detach=True,
                    volumes={os.path.abspath('.'): {'bind': '/app', 'mode': 'rw'}},
                    network="host",
                    environment={
                        "API_SERVER_URL": f"http://host.docker.internal:{args.port}"
                    },
                    name=f"node-{node_id}"
                )
                
                # Register the node
                self.nodes[node_id] = {
                    'cpu_cores': cpu_cores,
                    'available_cores': cpu_cores,
                    'status': 'healthy',
                    'pods': [],
                    'container_id': container.id
                }
                
                self.node_last_heartbeat[node_id] = time.time()
                
                logger.info(f"Node {node_id} added with {cpu_cores} CPU cores")
                return node_id, True
                
            except Exception as e:
                logger.error(f"Failed to add node with Docker: {str(e)}")
                # Fall back to simulation mode
                self.docker_client = None
        
        # If Docker is not available, simulate the node
        if self.docker_client is None:
            # Register the node without actually creating a Docker container
            self.nodes[node_id] = {
                'cpu_cores': cpu_cores,
                'available_cores': cpu_cores,
                'status': 'healthy',
                'pods': [],
                'container_id': 'simulation-mode'
            }
            
            self.node_last_heartbeat[node_id] = time.time()
            
            # Simulate heartbeats for this node
            threading.Thread(
                target=self._simulate_heartbeats, 
                args=(node_id,),
                daemon=True
            ).start()
            
            logger.info(f"Node {node_id} added in simulation mode with {cpu_cores} CPU cores")
            return node_id, True

    def _simulate_heartbeats(self, node_id):
        """Simulate heartbeats for a node in simulation mode"""
        self.nodes[node_id]['simulate_heartbeats'] = True
        while node_id in self.nodes and self.nodes[node_id].get('simulate_heartbeats', False):
            self.update_node_heartbeat(node_id)
            time.sleep(5)  # Send simulated heartbeat every 5 seconds

    def get_nodes(self):
        """Get all registered nodes and their status"""
        return self.nodes
    
    def update_node_heartbeat(self, node_id):
        """Update the last heartbeat time for a node"""
        if node_id in self.nodes:
            self.node_last_heartbeat[node_id] = time.time()
            self.nodes[node_id]['status'] = 'healthy'
            return True
        return False
    
    def mark_node_unhealthy(self, node_id):
        """Mark a node as unhealthy"""
        if node_id in self.nodes:
            self.nodes[node_id]['status'] = 'unhealthy'
            # Stop simulating heartbeats for this node
            self.nodes[node_id]['simulate_heartbeats'] = False
            return True
        return False
    
    def terminate_node(self, node_id):
        """Handle node termination"""
        if node_id in self.nodes:
            self.nodes[node_id]['status'] = 'unhealthy'
            # Stop simulating heartbeats for this node
            self.nodes[node_id]['simulate_heartbeats'] = False
            return True
        return False
    
    def get_healthy_nodes(self):
        """Get all healthy nodes"""
        return {node_id: node_info for node_id, node_info in self.nodes.items() 
                if node_info['status'] == 'healthy'}
    
    def add_pod_to_node(self, node_id, pod_id, cpu_requirement):
        """Add a pod to a node"""
        if node_id in self.nodes and self.nodes[node_id]['available_cores'] >= cpu_requirement:
            self.nodes[node_id]['pods'].append(pod_id)
            self.nodes[node_id]['available_cores'] -= cpu_requirement
            return True
        return False
    
    def get_pods_on_node(self, node_id):
        """Get all pods on a node"""
        if node_id in self.nodes:
            return self.nodes[node_id]['pods']
        return []
    
    def get_node_stats(self):
        """Get statistics about nodes in the cluster"""
        total_nodes = len(self.nodes)
        healthy_nodes = sum(1 for node_info in self.nodes.values() if node_info['status'] == 'healthy')
        unhealthy_nodes = total_nodes - healthy_nodes
        
        total_cores = sum(node_info['cpu_cores'] for node_info in self.nodes.values())
        available_cores = sum(node_info['available_cores'] for node_info in self.nodes.values())
        used_cores = total_cores - available_cores
        
        return {
            'total_nodes': total_nodes,
            'healthy_nodes': healthy_nodes,
            'unhealthy_nodes': unhealthy_nodes,
            'total_cores': total_cores,
            'available_cores': available_cores,
            'used_cores': used_cores
        }

class PodScheduler:
    def __init__(self, node_manager):
        self.node_manager = node_manager
        self.pods = {}  # Dictionary to store pod information {pod_id: {cpu_requirement, node_id}}
        self.last_node_index = -1  # For round-robin scheduling
    
    def schedule_pod(self, cpu_requirement, algorithm="first-fit"):
        """Schedule a pod on an available node based on the specified algorithm"""
        pod_id = str(uuid.uuid4())
        healthy_nodes = self.node_manager.get_healthy_nodes()
        
        if not healthy_nodes:
            logger.warning("No healthy nodes available for scheduling")
            return None, "No healthy nodes available"
        
        # Filter nodes with enough available cores
        eligible_nodes = {node_id: node_info for node_id, node_info in healthy_nodes.items() 
                         if node_info['available_cores'] >= cpu_requirement}
        
        if not eligible_nodes:
            logger.warning(f"No nodes with enough resources ({cpu_requirement} cores) available")
            return None, "Insufficient resources"
        
        selected_node_id = None
        
        # Apply scheduling algorithm
        if algorithm == "first-fit":
            # First-fit: Select the first node with enough resources
            selected_node_id = next(iter(eligible_nodes))
            
        elif algorithm == "best-fit":
            # Best-fit: Select the node with the least available resources that can still fit the pod
            selected_node_id = min(eligible_nodes, key=lambda node_id: eligible_nodes[node_id]['available_cores'])
            
        elif algorithm == "worst-fit":
            # Worst-fit: Select the node with the most available resources
            selected_node_id = max(eligible_nodes, key=lambda node_id: eligible_nodes[node_id]['available_cores'])
            
        elif algorithm == "round-robin":
            # Round-robin: Distribute pods evenly across nodes
            eligible_node_ids = list(eligible_nodes.keys())
            if eligible_node_ids:
                # Sort nodes by pod count for more even distribution
                sorted_nodes = sorted(eligible_node_ids, 
                                     key=lambda node_id: len(eligible_nodes[node_id]['pods']))
                selected_node_id = sorted_nodes[0]
                
        elif algorithm == "random-fit":
            # Random-fit: Randomly select a node from eligible nodes
            eligible_node_ids = list(eligible_nodes.keys())
            if eligible_node_ids:
                selected_node_id = random.choice(eligible_node_ids)
        
        # Add pod to the selected node
        if selected_node_id and self.node_manager.add_pod_to_node(selected_node_id, pod_id, cpu_requirement):
            # Store pod information
            self.pods[pod_id] = {
                'cpu_requirement': cpu_requirement,
                'node_id': selected_node_id,
                'algorithm': algorithm  # Store the algorithm used
            }
            
            logger.info(f"Pod {pod_id} scheduled on node {selected_node_id} with {cpu_requirement} CPU cores using {algorithm}")
            return pod_id, selected_node_id
        
        return None, "Failed to schedule pod"
    
    def get_pod_info(self, pod_id):
        """Get information about a pod"""
        return self.pods.get(pod_id)
    
    def get_all_pods(self):
        """Get all pods in the cluster"""
        return self.pods
    
    def reschedule_pods_from_node(self, failed_node_id):
        """Reschedule pods from a failed node to healthy nodes"""
        if failed_node_id not in self.node_manager.nodes:
            return False
        
        # Get pods on the failed node
        pods_to_reschedule = [(pod_id, pod_info) for pod_id, pod_info in self.pods.items() 
                             if pod_info['node_id'] == failed_node_id]
        
        if not pods_to_reschedule:
            logger.info(f"No pods to reschedule from node {failed_node_id}")
            return True
        
        logger.info(f"Rescheduling {len(pods_to_reschedule)} pods from failed node {failed_node_id}")
        
        # Reschedule each pod using their original scheduling algorithm
        for pod_id, pod_info in pods_to_reschedule:
            cpu_requirement = pod_info['cpu_requirement']
            algorithm = pod_info.get('algorithm', 'first-fit')  # Default to first-fit if not specified
            
            # Try to schedule the pod on a healthy node
            new_pod_id, new_node_id = self.schedule_pod(cpu_requirement, algorithm)
            
            if new_pod_id:
                logger.info(f"Pod {pod_id} from failed node {failed_node_id} rescheduled as {new_pod_id} on node {new_node_id}")
                # Remove the old pod
                del self.pods[pod_id]
            else:
                logger.warning(f"Failed to reschedule pod {pod_id} from failed node {failed_node_id}")
        
        return True
    
    def get_pod_stats(self):
        """Get statistics about pods in the cluster"""
        total_pods = len(self.pods)
        total_cpu_usage = sum(pod_info['cpu_requirement'] for pod_info in self.pods.values())
        
        # Count pods per node
        pods_per_node = {}
        for pod_id, pod_info in self.pods.items():
            node_id = pod_info['node_id']
            if node_id not in pods_per_node:
                pods_per_node[node_id] = 0
            pods_per_node[node_id] += 1
        
        return {
            'total_pods': total_pods,
            'total_cpu_usage': total_cpu_usage,
            'pods_per_node': pods_per_node
        }

class HealthMonitor:
    def __init__(self, node_manager, pod_scheduler):
        self.node_manager = node_manager
        self.pod_scheduler = pod_scheduler
        self.heartbeat_timeout = 15  # seconds
        self.monitoring_thread = None
        self.running = False
        
    def start_monitoring(self):
        """Start the health monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_nodes)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)
        logger.info("Health monitoring stopped")
    
    def _monitor_nodes(self):
        """Monitor node health based on heartbeats"""
        while self.running:
            current_time = time.time()
            
            for node_id, last_heartbeat in list(self.node_manager.node_last_heartbeat.items()):
                # Check if node has missed heartbeats
                if current_time - last_heartbeat > self.heartbeat_timeout:
                    logger.warning(f"Node {node_id} missed heartbeats, marking as unhealthy")
                    self.node_manager.mark_node_unhealthy(node_id)
                    
                    # Reschedule pods from the unhealthy node
                    self.pod_scheduler.reschedule_pods_from_node(node_id)
            
            time.sleep(5)  # Check every 5 seconds

# Initialize components
node_manager = NodeManager()
pod_scheduler = PodScheduler(node_manager)
health_monitor = HealthMonitor(node_manager, pod_scheduler)

# Start health monitoring
health_monitor.start_monitoring()

# API Endpoints
@app.route('/nodes', methods=['POST'])
def add_node():
    """API endpoint to add a new node to the cluster"""
    data = request.json
    cpu_cores = data.get('cpu_cores', 1)
    
    if not isinstance(cpu_cores, int) or cpu_cores <= 0:
        return jsonify({'error': 'CPU cores must be a positive integer'}), 400
    
    node_id, success = node_manager.add_node(cpu_cores)
    
    if success:
        return jsonify({
            'message': 'Node added successfully',
            'node_id': node_id,
            'cpu_cores': cpu_cores
        }), 201
    else:
        return jsonify({'error': 'Failed to add node'}), 500

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """API endpoint to list all nodes in the cluster"""
    nodes = node_manager.get_nodes()
    return jsonify({'nodes': nodes}), 200

@app.route('/nodes/<node_id>/heartbeat', methods=['POST'])
def node_heartbeat(node_id):
    """API endpoint to receive heartbeat signals from nodes"""
    success = node_manager.update_node_heartbeat(node_id)
    
    if success:
        return jsonify({'status': 'heartbeat received'}), 200
    else:
        return jsonify({'error': 'Node not found'}), 404

@app.route('/pods', methods=['POST'])
def create_pod():
    """API endpoint to create a new pod"""
    data = request.json
    cpu_requirement = data.get('cpu_requirement', 1)
    algorithm = data.get('algorithm', 'first-fit')
    
    if not isinstance(cpu_requirement, int) or cpu_requirement <= 0:
        return jsonify({'error': 'CPU requirement must be a positive integer'}), 400
    
    if algorithm not in ['first-fit', 'best-fit', 'worst-fit', 'round-robin', 'random-fit']:
        return jsonify({'error': 'Invalid scheduling algorithm'}), 400
    
    pod_id, node_id = pod_scheduler.schedule_pod(cpu_requirement, algorithm)
    
    if pod_id:
        return jsonify({
            'message': 'Pod created successfully',
            'pod_id': pod_id,
            'node_id': node_id,
            'cpu_requirement': cpu_requirement
        }), 201
    else:
        return jsonify({'error': f'Failed to create pod: {node_id}'}), 500

@app.route('/pods', methods=['GET'])
def get_pods():
    """API endpoint to list all pods in the cluster"""
    pods = pod_scheduler.get_all_pods()
    return jsonify({'pods': pods}), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """API endpoint to get cluster statistics"""
    node_stats = node_manager.get_node_stats()
    pod_stats = pod_scheduler.get_pod_stats()
    
    return jsonify({
        'nodes': node_stats,
        'pods': pod_stats
    }), 200

@app.route('/nodes/<node_id>/terminate', methods=['POST'])
def terminate_node(node_id):
    """API endpoint to handle node termination"""
    success = node_manager.terminate_node(node_id)
    if success:
        # Trigger pod rescheduling
        pod_scheduler.reschedule_pods_from_node(node_id)
        return jsonify({'status': 'node terminated'}), 200
    else:
        return jsonify({'error': 'Node not found'}), 404

@app.route('/', methods=['GET'])
def home():
    """API endpoint for the home page"""
    return jsonify({
        'message': 'Kubernetes-like Cluster Simulation API Server',
        'endpoints': {
            'GET /': 'This help message',
            'GET /nodes': 'List all nodes',
            'POST /nodes': 'Add a new node',
            'GET /pods': 'List all pods',
            'POST /pods': 'Create a new pod',
            'GET /stats': 'Get cluster statistics'
        }
    }), 200

if __name__ == '__main__':
    print(f"Starting API Server on port {args.port}...")
    print(f"Access the API server at http://localhost:{args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=True)
