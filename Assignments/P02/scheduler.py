import time

def fcfs(processes):
    """
    First-Come, First-Serve (FCFS) Scheduling Algorithm.
    Executes jobs in the order of arrival until completion.
    """
    if not processes:
        return []

    processes.sort(key=lambda p: p.arrival_time)  # Sort by arrival time
    current_time = 0  # Initialize the simulation clock
    completed_processes = []  # List to store completed processes

    for process in processes:
        # If CPU is idle, move the clock to the process's arrival time
        if current_time < process.arrival_time:
            current_time = process.arrival_time
        
        # Start and complete the current process
        process.start_time = current_time
        current_time += process.burst_time  # Advance clock by burst time
        process.completion_time = current_time

        # Calculate metrics
        process.calculate_metrics(current_time)
        completed_processes.append(process)  # Add to completed list

    return completed_processes

def sjf_non_preemptive(processes):
    """
    Shortest Job First (Non-Preemptive) Scheduling Algorithm.
    Executes processes in the order of shortest burst time among those ready.
    """
    if not processes:
        return []

    completed = []
    current_time = 0

    while processes:
        # Get processes that have arrived
        ready_queue = [p for p in processes if p.arrival_time <= current_time]

        if ready_queue:
            # Select the process with the shortest burst time
            shortest_job = min(ready_queue, key=lambda p: (p.burst_time, p.arrival_time))
            processes.remove(shortest_job)

            if current_time < shortest_job.arrival_time:
                current_time = shortest_job.arrival_time
            shortest_job.start_time = current_time
            current_time += shortest_job.burst_time
            shortest_job.completion_time = current_time
            shortest_job.calculate_metrics(current_time)
            completed.append(shortest_job)
        else:
            current_time += 1  # If no process is ready, increment time

    return completed

def round_robin(processes, time_quantum, progress=None, task_map=None):
    """
    Round Robin (RR) Scheduling Algorithm with optional visualized progress.
    Executes processes in time slices of the given quantum.
    """
    if not processes or time_quantum <= 0:
        return []

    queue = processes[:]
    current_time = 0
    completed = []

    while queue:
        process = queue.pop(0)
        if process.start_time is None:
            process.start_time = max(current_time, process.arrival_time)

        time_to_execute = min(process.remaining_time, time_quantum)
        for _ in range(time_to_execute):
            current_time += 1
            process.remaining_time -= 1
            if progress and task_map:
                progress.advance(task_map[process.pid], 1)  # Update progress bar
                progress.refresh()  # Force refresh
            time.sleep(0.1)  # Simulate real-time execution

        if process.remaining_time == 0:
            process.completion_time = current_time
            process.calculate_metrics(current_time)
            completed.append(process)
        else:
            queue.append(process)

    return completed

def priority_non_preemptive(processes):
    """
    Priority Scheduling Non-Preemptive Algorithm.
    Executes the process with the highest priority among those ready.
    """
    if not processes:
        return []

    completed = []
    current_time = 0

    while processes:
        # Get processes that have arrived
        ready_queue = [p for p in processes if p.arrival_time <= current_time]

        if ready_queue:
            # Select the process with the highest priority (lower value = higher priority)
            highest_priority = min(ready_queue, key=lambda p: (p.priority, p.arrival_time))
            processes.remove(highest_priority)

            if current_time < highest_priority.arrival_time:
                current_time = highest_priority.arrival_time
            highest_priority.start_time = current_time
            current_time += highest_priority.burst_time
            highest_priority.completion_time = current_time
            highest_priority.calculate_metrics(current_time)
            completed.append(highest_priority)
        else:
            current_time += 1  # If no process is ready, increment time

    return completed

def mlfq(self, processes, progress=None, task_map=None, num_queues=3, base_time_quantum=4, time_quantums=None, algorithms=None):
    """
    Multi-Level Feedback Queue (MLFQ) Scheduling Algorithm with Rich Visualization.

    Args:
        processes: List of Process objects.
        progress: Rich progress object for visualization.
        task_map: Mapping of process IDs to Rich progress tasks.
        num_queues: Number of priority queues.
        base_time_quantum: Base time quantum for the highest-priority queue.
        time_quantums: List of time quanta for each queue.
        algorithms: List of algorithms for each queue (e.g., round_robin, sjf, fcfs).

    Returns:
        List of completed processes.
    """
    if not processes:
        return []

    # Default time_quantums for each queue if not provided
    time_quantums = time_quantums or [base_time_quantum * (i + 1) for i in range(num_queues)]
    algorithms = algorithms or ["round_robin"] * num_queues  # Default to Round Robin for all queues

    queues = [[] for _ in range(num_queues)]
    current_time = 0
    completed = []

    # Initially place all processes in Queue 1 (highest priority)
    for process in processes:
        queues[0].append(process)

    # Process each queue and simulate execution
    while any(queue for queue in queues):
        for level, queue in enumerate(queues):
            time_quantum = time_quantums[level]  # Get the time quantum for the current queue
            algorithm = algorithms[level]  # Get the algorithm for the current queue

            while queue:
                process = queue.pop(0)
                if process.start_time is None:
                    process.start_time = max(current_time, process.arrival_time)

                task = task_map.get(process.pid) if task_map else None

                # Execute the process based on the selected algorithm
                if algorithm == "round_robin":
                    time_to_execute = min(process.remaining_time, time_quantum)
                    for _ in range(time_to_execute):
                        process.remaining_time -= 1
                        current_time += 1
                        if task and progress:
                            progress.advance(task, 1)
                            progress.refresh()
                        time.sleep(0.1)  # Simulate real-time execution

                # Implement SJF, FCFS, or other algorithms similarly...

                # Process completion
                if process.remaining_time == 0:
                    process.completion_time = current_time
                    process.calculate_metrics(current_time)
                    completed.append(process)
                else:
                    if level < num_queues - 1:
                        queues[level + 1].append(process)
                    else:
                        queue.append(process)

                # Update the queue states dynamically for visualization
                if progress:
                    queue_states = "\n".join(
                        f"Queue {i + 1}: {[p.pid for p in q]}" for i, q in enumerate(queues)
                    )
                    progress.console.clear()
                    progress.console.print(queue_states)

    return completed



