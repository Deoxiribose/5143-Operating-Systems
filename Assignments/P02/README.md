# CPU Scheduler Simulation Overview

This code implements an interactive CPU scheduling simulation environment, where users can add processes, choose scheduling algorithms, and run simulations to analyze CPU performance.

**Key Capabilities:**

- **Process Management**:  
  Add new processes with specified arrival times, burst times, and priorities, or generate a set of random processes for testing.

- **Scheduling Algorithms**:  
  Select from a variety of CPU scheduling algorithms, including:  
  - **FCFS (First-Come, First-Serve)**  
  - **SJF (Shortest Job First)**  
  - **RR (Round Robin)** with a suggested time quantum based on average burst time  
  - **Priority Scheduling** (non-preemptive)

- **Single-Core and Multi-Core Modes**:  
  - **Single-Core Mode**: Run the chosen scheduling algorithm on a single CPU core.  
  - **Multi-Core Mode**: Distribute processes across multiple CPU cores using load-balancing strategies (e.g., `round_robin` or `least_loaded`).

- **Metrics and Analysis**:  
  After simulation, review key performance metrics such as average waiting time, turnaround time, and more, to understand the impact of different algorithms and configurations.

**How to Use**:  
- **Interactive Commands**: Enter commands like `add`, `randomize`, `algo`, and `start` to manage processes, choose algorithms, and run the simulation.  
- **Load-Balancing Strategies (Multicore)**: Use `strategy` to select how processes are assigned to multiple cores.  
- **Suggested Time Quantum**: For Round Robin, the simulation suggests a time quantum based on the average burst time of the currently loaded processes.

This CPU Scheduler Simulation enables users to experiment with different scheduling scenarios, compare algorithms, and gain insights into CPU performance.  
