import time
import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from process import Process
from scheduler import fcfs, sjf_non_preemptive, round_robin, priority_non_preemptive
from metrics import display_metrics
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from process import Process
from scheduler import fcfs, sjf_non_preemptive, round_robin, priority_non_preemptive
import time
from logger import Logger
from core import Core

class CPUSimulator:
    def __init__(self, num_cores=1):
        self.num_cores = num_cores
        self.cores = [Core(core_id=i) for i in range(num_cores)]  # Initialize cores
        self.ready_queue = []  # Shared ready queue
        self.completed_processes = []  # Shared completed processes
        self.next_pid = 1  # For assigning process IDs dynamically
        self.algorithm = None  # Scheduling algorithm
        self.time_quantum = None  # Time quantum needed for Round Robin
        self.global_clock = 0  # Initialize global clock

        self.console = Console()
        self.logger = Logger()
        
    def add_process(self, process):
        """
        Adds a new process to the ready queue and logs the event.
        """
        self.ready_queue.append(process)
        self.console.print(
            f"At time [bold blue]{self.global_clock}[/bold blue]: Process [bold yellow]P{process.pid}[/bold yellow] added to the ready queue."
        )

    def simulate(self):
        """
        Simulates the selected scheduling algorithm with progress bars and logging.
        """
        self.logger.reset_log()
        self.console.print(f"Starting simulation using [bold magenta]{self.algorithm.__name__.title()}[/bold magenta]...")

        if not self.ready_queue:
            self.console.print("[bold red]No processes in the ready queue to simulate.[/bold red]")
            return

        # Sort the ready queue if needed (specific to the algorithm)
        if self.algorithm == fcfs:
            self.ready_queue.sort(key=lambda p: p.arrival_time)
        elif self.algorithm == sjf_non_preemptive:
            self.ready_queue.sort(key=lambda p: (p.burst_time, p.arrival_time))

        # Execute the selected scheduling algorithm
        if self.algorithm == round_robin:
            self.completed_processes = self.algorithm(self.ready_queue, self.time_quantum)
        else:
            self.completed_processes = self.algorithm(self.ready_queue)

        # Progress Bar Configuration
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[bold green]{task.fields[info]}"),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            task_map = {}

            # Add tasks to the progress bar
            for process in self.completed_processes:
                task = progress.add_task(
                    f"[bold yellow]P{process.pid}[/bold yellow]",
                    total=process.burst_time,
                    info=f"Arrival: {process.arrival_time}, Burst: {process.burst_time}, Priority: {process.priority}",
                )
                task_map[process.pid] = task

            # Simulate each process
            while any(p.remaining_time > 0 for p in self.completed_processes):
                for process in self.completed_processes:
                    if process.remaining_time > 0:
                        progress.advance(task_map[process.pid])
                        process.remaining_time -= 1
                        self.global_clock += 1  # Increment global clock
                        time.sleep(0.5)  # Simulate time unit

                        # Log process details when completed
                        if process.remaining_time == 0 and process.completion_time is None:
                            process.completion_time = self.global_clock
                            process.calculate_metrics(self.global_clock)
                            self.log_process(process)

        self.console.print("[bold green]Simulation complete![/bold green]")
        self.analyze_metrics()

    def log_process(self, process):
        """
        Logs process metrics to the log file.
        """
        process_data = {
            "PID": process.pid,
            "Arrival Time": process.arrival_time,
            "Burst Time": process.burst_time,
            "Completion Time": process.completion_time,
            "Waiting Time": process.waiting_time,
            "Turnaround Time": process.turnaround_time,
        }
        self.logger.log(process_data)

    def set_algorithm(self, algorithm_name):
        """
        Sets the scheduling algorithm to use.
        """
        if algorithm_name == "fcfs":
            self.algorithm = fcfs
        elif algorithm_name == "sjf":
            self.algorithm = sjf_non_preemptive
        elif algorithm_name == "rr":
            self.algorithm = round_robin
        elif algorithm_name == "priority":
            self.algorithm = priority_non_preemptive

    def randomize_processes(self, num_processes):
        import random
        for _ in range(num_processes):
            pid = self.next_pid
            arrival_time = random.randint(0, 10)
            burst_time = random.randint(1, 10)
            priority = random.randint(1, 5)
            self.add_process(Process(pid, arrival_time, burst_time, priority))
            self.next_pid += 1
        self.console.print(f"[bold green]{num_processes} random processes have been added to the ready queue.[/bold green]")
  
    def display_metrics(self):
        """
        Displays metrics for completed processes.
        """
        from metrics import display_metrics
        display_metrics(self.completed_processes)
        
    def analyze_metrics(self):
        """
        Calculates and displays summary metrics for the simulation.
        """
        if not self.completed_processes:
            self.console.print("[bold red]No completed processes to analyze.[/bold red]")
            return

        total_waiting_time = sum(p.waiting_time for p in self.completed_processes)
        total_turnaround_time = sum(p.turnaround_time for p in self.completed_processes)
        total_burst_time = sum(p.burst_time for p in self.completed_processes)

        # Ensure Total Simulation Time accounts for idle periods
        earliest_arrival = min(p.arrival_time for p in self.completed_processes)
        latest_completion = max(p.completion_time for p in self.completed_processes)
        total_simulation_time = latest_completion - earliest_arrival

        # Avoid division by zero or negative times
        if total_simulation_time <= 0:
            self.console.print("[bold red]Simulation time is invalid.[/bold red]")
            return

        # Calculate metrics
        average_waiting_time = total_waiting_time / len(self.completed_processes)
        average_turnaround_time = total_turnaround_time / len(self.completed_processes)
        cpu_utilization = (total_burst_time / total_simulation_time) * 100

        # Display Results
        self.console.print("\n[bold magenta]--- Simulation Metrics ---[/bold magenta]")
        self.console.print(f"[bold blue]Average Waiting Time:[/bold blue] {average_waiting_time:.2f} units")
        self.console.print(f"[bold blue]Average Turnaround Time:[/bold blue] {average_turnaround_time:.2f} units")
        self.console.print(f"[bold blue]CPU Utilization:[/bold blue] {min(cpu_utilization, 100):.2f}%")

    def assign_processes_to_cores(self, strategy="round_robin", algorithms=None):
        """
        Distribute processes across cores and set algorithms.

        Args:
            strategy (str): Load balancing strategy ('round_robin' or 'least_loaded').
            algorithms (dict): Optional mapping of core_id to algorithm names.
        """
        # Assign processes using the chosen strategy
        if strategy == "round_robin":
            for i, process in enumerate(self.ready_queue):
                self.cores[i % len(self.cores)].add_process(process)
        elif strategy == "least_loaded":
            for process in self.ready_queue:
                least_loaded_core = min(self.cores, key=lambda core: len(core.queue))
                least_loaded_core.add_process(process)

        # Set algorithms for each core (if provided)
        if algorithms:
            for core_id, algorithm_name in algorithms.items():
                self.cores[core_id].algorithm = algorithm_name

    def auto_select_algorithm(self):
        """
        Automatically selects the best scheduling algorithm based on process characteristics.
        """
        if not self.ready_queue:
            self.console.print("[bold red]No processes in the ready queue to analyze.[/bold red]")
            return

        # Analyze process characteristics
        burst_times = [p.burst_time for p in self.ready_queue]
        priorities = [p.priority for p in self.ready_queue]

        # Algorithm selection logic
        if len(set(priorities)) > 1:  # Processes with different priorities
            self.set_algorithm("priority")
            self.console.print("[bold magenta]Optimal algorithm selected: Priority Scheduling.[/bold magenta]")
        elif max(burst_times) <= 10:  # Short tasks
            self.set_algorithm("sjf")
            self.console.print("[bold magenta]Optimal algorithm selected: Shortest Job First (SJF).[/bold magenta]")
        elif len(self.ready_queue) > 4:  # Overloaded system
            self.set_algorithm("rr")
            self.time_quantum = max(2, sum(burst_times) // len(burst_times))  # Suggested time quantum
            self.console.print(f"[bold magenta]Optimal algorithm selected: Round Robin with Time Quantum = {self.time_quantum}.[/bold magenta]")
        else:  # Default fallback
            self.set_algorithm("fcfs")
            self.console.print("[bold magenta]Optimal algorithm selected: First-Come, First-Serve (FCFS).[/bold magenta]")



