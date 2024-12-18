from simulation import CPUSimulator
from process import Process

def suggest_time_quantum(processes):
    """
    Suggests a time quantum based on the average burst time of the processes.
    Args:
        processes (list): List of Process objects.

    Returns:
        int: Suggested time quantum based on average burst time.
    """
    if not processes:
        return 1  # Default to 1 if no processes exist
    total_burst_time = sum(p.burst_time for p in processes)
    return max(1, total_burst_time // len(processes))  # Ensure time quantum is at least 1


def multicore_menu():
    """
    Menu for multicore simulation functionality.
    """
    print("\nWelcome to the Multicore Simulation Shell!")
    print("Type 'help' for a list of multicore commands.")
    num_cores = 2  # Default number of cores
    multicore_simulator = CPUSimulator(num_cores=num_cores)

    while True:
        command = input("Multicore_Sim> ").strip().lower()

        if command == "help":
            print("\nMulticore Commands:")
            print("  setcores          - Set the number of CPU cores")
            print("  add               - Add a new process manually")
            print("  randomize         - Add random processes")
            print("  strategy          - Choose load-balancing strategy")
            print("  algo              - Select a scheduling algorithm")
            print("  start             - Start multicore simulation")
            print("  metrics           - Display multicore metrics")
            print("  back              - Return to the main menu")

        elif command == "setcores":
            try:
                num_cores = int(input("Enter the number of CPU cores: "))
                multicore_simulator = CPUSimulator(num_cores=num_cores)
                print(f"Number of cores set to {num_cores}.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

        elif command == "add":
            pid = multicore_simulator.next_pid
            try:
                arrival_time = int(input("Enter arrival time: "))
                burst_time = int(input("Enter burst time: "))
                priority = int(input("Enter priority (lower is higher priority): "))
                multicore_simulator.add_process(Process(pid, arrival_time, burst_time, priority))
                multicore_simulator.next_pid += 1
                print(f"Process P{pid} added.")
            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        elif command == "randomize":
            try:
                num_processes = int(input("Enter number of random processes to add: "))
                multicore_simulator.randomize_processes(num_processes)
                print(f"{num_processes} random processes added.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

        elif command == "strategy":
            strategy = input("Enter load-balancing strategy (round_robin / least_loaded): ").strip().lower()
            if strategy in {"round_robin", "least_loaded"}:
                multicore_simulator.assign_processes_to_cores(strategy=strategy)
                print(f"Load-balancing strategy set to {strategy}.")
            else:
                print("Invalid strategy. Choose 'round_robin' or 'least_loaded'.")

        elif command == "algo":
            if not multicore_simulator.ready_queue:
                print("No processes available. Add or randomize processes first.")
            else:
                print("\nAvailable algorithms:")
                print("  1. FCFS (First-Come, First-Serve)")
                print("  2. SJF (Shortest Job First)")
                print("  3. RR (Round Robin)")
                print("  4. Priority (Non-Preemptive)")

                choice = input("Enter your choice (number or name): ").strip().lower()
                if choice in {"1", "fcfs"}:
                    multicore_simulator.set_algorithm("fcfs")
                    print("Algorithm set to FCFS.")
                elif choice in {"2", "sjf"}:
                    multicore_simulator.set_algorithm("sjf")
                    print("Algorithm set to SJF.")
                elif choice in {"3", "rr"}:
                    multicore_simulator.set_algorithm("rr")
                    suggested_tq = suggest_time_quantum(multicore_simulator.ready_queue)
                    print(f"Suggested Time Quantum: {suggested_tq} (based on average burst time).")
                    multicore_simulator.time_quantum = int(input("Enter time quantum (or press Enter to use suggested): ") or suggested_tq)
                    print(f"Algorithm set to Round Robin with Time Quantum = {multicore_simulator.time_quantum}.")
                elif choice in {"4", "priority"}:
                    multicore_simulator.set_algorithm("priority")
                    print("Algorithm set to Priority Scheduling.")
                else:
                    print("Invalid choice. Please select a valid algorithm.")

        elif command == "start":
            multicore_simulator.simulate()

        elif command == "metrics":
            multicore_simulator.analyze_metrics()

        elif command == "back":
            print("Returning to the main menu.")
            break

        else:
            print("Unknown command. Type 'help' for a list of multicore commands.")


def main():
    """
    Main menu for single-core and multicore simulation.
    """
    simulator = CPUSimulator()
    print("Welcome to the CPU Scheduling Simulator Shell!")
    print("Type 'help' for a list of commands.")

    while True:
        command = input("CPU_Sim> ").strip().lower()

        if command == "help":
            print("\nCommands:")
            print("  add               - Add a new process manually (single-core)")
            print("  randomize         - Add a random process (single-core)")
            print("  algo              - Select a scheduling algorithm (single-core)")
            print("  start             - Start the simulation (single-core)")
            print("  metrics           - Display performance metrics (single-core)")
            print("  multicore         - Switch to multicore simulation menu")
            print("  exit              - Exit the simulator")

        elif command == "add":
            pid = simulator.next_pid
            try:
                arrival_time = int(input("Enter arrival time: "))
                burst_time = int(input("Enter burst time: "))
                priority = int(input("Enter priority (lower is higher priority): "))
                simulator.add_process(Process(pid, arrival_time, burst_time, priority))
                simulator.next_pid += 1
                print(f"Process P{pid} added.")
            except ValueError:
                print("Invalid input. Please enter valid numbers.")

        elif command == "randomize":
            try:
                num_processes = int(input("Enter number of random processes to add: "))
                simulator.randomize_processes(num_processes)
                print(f"{num_processes} random processes added.")
            except ValueError:
                print("Invalid input. Please enter a valid number.")

        elif command == "algo":
            if not simulator.ready_queue:
                print("No processes available. Add or randomize processes first.")
            else:
                print("\nAvailable algorithms:")
                print("  1. FCFS (First-Come, First-Serve)")
                print("  2. SJF (Shortest Job First)")
                print("  3. RR (Round Robin)")
                print("  4. Priority (Non-Preemptive)")

                choice = input("Enter your choice (number or name): ").strip().lower()
                if choice in {"1", "fcfs"}:
                    simulator.set_algorithm("fcfs")
                    print("Algorithm set to FCFS.")
                elif choice in {"2", "sjf"}:
                    simulator.set_algorithm("sjf")
                    print("Algorithm set to SJF.")
                elif choice in {"3", "rr"}:
                    simulator.set_algorithm("rr")
                    suggested_tq = suggest_time_quantum(simulator.ready_queue)
                    print(f"Suggested Time Quantum: {suggested_tq} (based on average burst time).")
                    simulator.time_quantum = int(input("Enter time quantum (or press Enter to use suggested): ") or suggested_tq)
                    print(f"Algorithm set to Round Robin with Time Quantum = {simulator.time_quantum}.")
                elif choice in {"4", "priority"}:
                    simulator.set_algorithm("priority")
                    print("Algorithm set to Priority Scheduling.")
                else:
                    print("Invalid choice. Please select a valid algorithm.")

        elif command == "start":
            simulator.simulate()

        elif command == "metrics":
            simulator.display_metrics()

        elif command == "multicore":
            multicore_menu()

        elif command == "exit":
            print("Exiting simulation. Goodbye!")
            break

        else:
            print("Unknown command. Type 'help' for a list of commands.")


if __name__ == "__main__":
    main()
