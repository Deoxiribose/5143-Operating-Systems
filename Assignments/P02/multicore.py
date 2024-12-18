def assign_processes_to_cores(processes, num_cores, strategy="least_loaded"):
    """
    Distributes processes across multiple CPU cores based on the chosen strategy.

    Args:
        processes (list): List of Process objects.
        num_cores (int): Number of CPU cores.
        strategy (str): Load balancing strategy ('round_robin' or 'least_loaded').

    Returns:
        list: A list of queues (one per core) containing assigned processes.
    """
    core_queues = [[] for _ in range(num_cores)]

    if strategy == "round_robin":
        # Distribute processes cyclically across cores
        for i, process in enumerate(processes):
            core_id = i % num_cores
            process.core_id = core_id
            core_queues[core_id].append(process)

    elif strategy == "least_loaded":
        # Assign each process to the core with the smallest total burst time
        for process in processes:
            least_loaded_core = min(core_queues, key=lambda queue: sum(p.burst_time for p in queue))
            core_id = core_queues.index(least_loaded_core)
            process.core_id = core_id
            core_queues[core_id].append(process)

    return core_queues

def simulate_multicore_execution(core_queues, scheduling_algorithm):
    """
    Simulates execution of processes on multiple CPU cores.

    Args:
        core_queues (list): List of queues (one per core) with assigned processes.
        scheduling_algorithm (function): Scheduling algorithm to run on each core.

    Returns:
        list: List of scheduled processes for all cores.
    """
    scheduled_processes = []
    for core_id, queue in enumerate(core_queues):
        print(f"\nSimulating Core {core_id}...")
        # Run the scheduling algorithm on each core's queue
        core_scheduled = scheduling_algorithm(queue)
        for process in core_scheduled:
            process.core_id = core_id  # Ensure core_id is preserved
        scheduled_processes.extend(core_scheduled)

    return scheduled_processes
