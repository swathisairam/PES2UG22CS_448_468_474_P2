import requests
import argparse
import json
import sys
import time
import os
from tabulate import tabulate

# Default API server URL with port 5001 (changed from 5000)
API_SERVER_URL = "http://localhost:5001"

def add_node(args):
    """Add a new node to the cluster"""
    try:
        response = requests.post(
            f"{API_SERVER_URL}/nodes",
            json={'cpu_cores': args.cpu_cores}
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"Node added successfully!")
            print(f"Node ID: {data['node_id']}")
            print(f"CPU Cores: {data['cpu_cores']}")
        else:
            print(f"Failed to add node: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def list_nodes(args):
    """List all nodes in the cluster"""
    try:
        response = requests.get(f"{API_SERVER_URL}/nodes")
        
        if response.status_code == 200:
            data = response.json()
            nodes = data.get('nodes', {})
            
            if not nodes:
                print("No nodes found in the cluster.")
                return
            
            # Prepare table data
            table_data = []
            for node_id, node_info in nodes.items():
                table_data.append([
                    node_id,
                    node_info['cpu_cores'],
                    node_info['available_cores'],
                    node_info['status'],
                    ', '.join(node_info['pods']) if node_info['pods'] else 'None'
                ])
            
            # Print table
            print("\nNodes in the cluster:")
            print(tabulate(
                table_data,
                headers=['Node ID', 'CPU Cores', 'Available', 'Status', 'Pods'],
                tablefmt='grid'
            ))
                
        else:
            print(f"Failed to list nodes: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def create_pod(args):
    """Create a new pod in the cluster"""
    try:
        response = requests.post(
            f"{API_SERVER_URL}/pods",
            json={
                'cpu_requirement': args.cpu_requirement,
                'algorithm': args.algorithm
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"Pod created successfully!")
            print(f"Pod ID: {data['pod_id']}")
            print(f"Scheduled on Node: {data['node_id']}")
            print(f"CPU Requirement: {data['cpu_requirement']}")
        else:
            print(f"Failed to create pod: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def list_pods(args):
    """List all pods in the cluster"""
    try:
        response = requests.get(f"{API_SERVER_URL}/pods")
        
        if response.status_code == 200:
            data = response.json()
            pods = data.get('pods', {})
            
            if not pods:
                print("No pods found in the cluster.")
                return
            
            # Prepare table data
            table_data = []
            for pod_id, pod_info in pods.items():
                table_data.append([
                    pod_id,
                    pod_info['cpu_requirement'],
                    pod_info['node_id']
                ])
            
            # Print table
            print("\nPods in the cluster:")
            print(tabulate(
                table_data,
                headers=['Pod ID', 'CPU Requirement', 'Node ID'],
                tablefmt='grid'
            ))
                
        else:
            print(f"Failed to list pods: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def show_stats(args):
    """Show cluster statistics"""
    try:
        response = requests.get(f"{API_SERVER_URL}/stats")
        
        if response.status_code == 200:
            data = response.json()
            node_stats = data.get('nodes', {})
            pod_stats = data.get('pods', {})
            
            print("\n=== Cluster Statistics ===\n")
            
            print("Node Statistics:")
            print(f"Total Nodes: {node_stats.get('total_nodes', 0)}")
            print(f"Healthy Nodes: {node_stats.get('healthy_nodes', 0)}")
            print(f"Unhealthy Nodes: {node_stats.get('unhealthy_nodes', 0)}")
            print(f"Total CPU Cores: {node_stats.get('total_cores', 0)}")
            print(f"Available CPU Cores: {node_stats.get('available_cores', 0)}")
            print(f"Used CPU Cores: {node_stats.get('used_cores', 0)}")
            
            print("\nPod Statistics:")
            print(f"Total Pods: {pod_stats.get('total_pods', 0)}")
            print(f"Total CPU Usage: {pod_stats.get('total_cpu_usage', 0)}")
            
            pods_per_node = pod_stats.get('pods_per_node', {})
            if pods_per_node:
                print("\nPods per Node:")
                for node_id, pod_count in pods_per_node.items():
                    print(f"  Node {node_id}: {pod_count} pods")
                
        else:
            print(f"Failed to get statistics: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Kubernetes-like Cluster Simulation CLI")
    
    # Add optional argument to specify API server URL
    parser.add_argument("--api-url", help="API server URL (default: http://localhost:5001)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add node command
    add_node_parser = subparsers.add_parser("add-node", help="Add a new node to the cluster")
    add_node_parser.add_argument("--cpu-cores", type=int, default=1, help="Number of CPU cores for the node")
    
    # List nodes command
    list_nodes_parser = subparsers.add_parser("list-nodes", help="List all nodes in the cluster")
    
    # Create pod command
    create_pod_parser = subparsers.add_parser("create-pod", help="Create a new pod in the cluster")
    create_pod_parser.add_argument("--cpu-requirement", type=int, default=1, help="CPU requirement for the pod")
    create_pod_parser.add_argument("--algorithm", choices=["first-fit", "best-fit", "worst-fit"], default="first-fit", 
                                  help="Scheduling algorithm to use")
    
    # List pods command
    list_pods_parser = subparsers.add_parser("list-pods", help="List all pods in the cluster")
    
    # Show stats command
    show_stats_parser = subparsers.add_parser("show-stats", help="Show cluster statistics")
    
    args = parser.parse_args()
    
    # Update API server URL if provided
    global API_SERVER_URL
    if args.api_url:
        API_SERVER_URL = args.api_url
    
    if args.command == "add-node":
        add_node(args)
    elif args.command == "list-nodes":
        list_nodes(args)
    elif args.command == "create-pod":
        create_pod(args)
    elif args.command == "list-pods":
        list_pods(args)
    elif args.command == "show-stats":
        show_stats(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
