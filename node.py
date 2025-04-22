import requests
import time
import sys
import uuid
import logging
import signal
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Node:
    def __init__(self, node_id, cpu_cores):
        self.node_id = node_id
        self.cpu_cores = int(cpu_cores)
        self.available_cores = self.cpu_cores
        self.pods = []  # List to store pod IDs
        
        # Get API server URL from environment variable or use default
        self.api_server_url = os.environ.get("API_SERVER_URL", "http://localhost:5001")
        logger.info(f"Using API server URL: {self.api_server_url}")
        
        self.running = True
    
    def send_heartbeat(self):
        """Send heartbeat signal to the API server"""
        try:
            response = requests.post(
                f"{self.api_server_url}/nodes/{self.node_id}/heartbeat",
                json={
                    'status': 'healthy',
                    'available_cores': self.available_cores,
                    'pods': self.pods
                }
            )
            
            if response.status_code == 200:
                logger.debug(f"Node {self.node_id}: Heartbeat sent successfully")
            else:
                logger.warning(f"Node {self.node_id}: Failed to send heartbeat - {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Node {self.node_id}: Error sending heartbeat - {str(e)}")
    
    def start_heartbeat_loop(self):
        """Start sending periodic heartbeats to the API server"""
        logger.info(f"Node {self.node_id}: Starting heartbeat loop")
        
        while self.running:
            self.send_heartbeat()
            time.sleep(5)  # Send heartbeat every 5 seconds
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Node {self.node_id}: Shutting down...")
        self.running = False

def main():
    # Get node ID and CPU cores from environment variables or command line
    node_id = os.environ.get("NODE_ID")
    cpu_cores = os.environ.get("CPU_CORES")
    
    if not node_id or not cpu_cores:
        # Fall back to command line arguments if env vars not provided
        if len(sys.argv) < 3:
            logger.error("Usage: python node.py <node_id> <cpu_cores>")
            logger.error("Or set NODE_ID and CPU_CORES environment variables")
            sys.exit(1)
        node_id = sys.argv[1]
        cpu_cores = sys.argv[2]
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, lambda signum, frame: node.handle_shutdown(signum, frame))
    signal.signal(signal.SIGINT, lambda signum, frame: node.handle_shutdown(signum, frame))
    
    # Create and start the node
    node = Node(node_id, cpu_cores)
    
    logger.info(f"Node {node_id} started with {cpu_cores} CPU cores")
    
    # Start sending heartbeats
    node.start_heartbeat_loop()

if __name__ == "__main__":
    main()
