#!/bin/bash
curl -X POST http://localhost:5000/add_node -H "Content-Type: application/json" -d '{"cpu_cores": 4}'
