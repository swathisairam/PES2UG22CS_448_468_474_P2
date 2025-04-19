# PES2UG22CS_448_468_474_P2

✅ Week 1:
Focus: Initial Setup — API Server & Node Addition
Tasks:
  Implement API Server with Node Manager functionality.
  Add Nodes (simulate by launching a new Docker container).
  Each node must:
     Specify CPU cores
     Register itself with the API server
     Periodically send heartbeat signals to confirm availability
Goal: Establish the cluster base — enable dynamic node joining.

✅ Week 2:
Focus: Pod Scheduling & Health Monitoring
Tasks:
   Implement:
    Pod Scheduler (using scheduling algorithms like First-Fit, Best-Fit, Worst-Fit)
    Health Monitor to detect node failures
   Add Pod Functionality:
    Clients can launch pods by specifying required CPU
   System automatically assigns pod to a suitable node
     Pod is added to node’s array list of pod IDs
Goal: Functional cluster with intelligent pod placement and node health checks.

✅ Week 3:
Focus: Listing, Testing, Documentation
Tasks:
  Implement functionality to list all nodes and their current health status
  Conduct system testing
  Prepare documentation
Goal: Validate complete functionality and prepare for final evaluation.

