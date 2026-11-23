
import socket
import threading
import time


# ==========================================
# 1. LOAD BALANCER CONFIGURATION
# ==========================================

LB_HOST = "127.0.0.1"
LB_PORT = 9000

BACKENDS = [
    ("Server-1", "127.0.0.1", 9001),
    ("Server-2", "127.0.0.1", 9002),
    ("Server-3", "127.0.0.1", 9003),
]

HEALTH_INTERVAL = 2
HEALTH_TIMEOUT = 1


# ==========================================
# 2. ROUND ROBIN SCHEDULER
# ==========================================

class RoundRobinScheduler:

    def __init__(self, backends):
        self.backends = backends
        self.next_index = 0

        self.status = {
            name: True for name, _, _ in backends
        }

        self.lock = threading.Lock()

    def next_backend(self, excluded=None):
        """Select the next healthy backend."""

        if excluded is None:
            excluded = set()

        with self.lock:

            total = len(self.backends)

            for offset in range(total):

                index = (self.next_index + offset) % total

                backend = self.backends[index]
                name = backend[0]

                if self.status[name] and name not in excluded:

                    self.next_index = (index + 1) % total

                    return backend

            return None

    def set_status(self, name, is_up):
        """Update backend health status."""

        with self.lock:

            changed = self.status[name] != is_up

            self.status[name] = is_up

            return changed

    def get_status(self, name):

        with self.lock:
            return self.status[name]


# ==========================================
# 3. GLOBAL OBJECTS AND STATISTICS
# ==========================================

scheduler = RoundRobinScheduler(BACKENDS)

request_count = 0

stats_lock = threading.Lock()

stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "retries": 0,

    "server_success": {
        name: 0 for name, _, _ in BACKENDS
    },

    "server_failures": {
        name: 0 for name, _, _ in BACKENDS
    }
}


# ==========================================
# 4. BACKEND HEALTH CHECKER
# ==========================================

def check_backend(host, port):
    """Check whether a backend accepts TCP connections."""

    try:

        with socket.create_connection(
            (host, port),
            timeout=HEALTH_TIMEOUT
        ):
            return True

    except OSError:
        return False


def check_all_backends():
    """Check all backend servers."""

    for name, host, port in BACKENDS:

        is_up = check_backend(host, port)

        if scheduler.set_status(name, is_up):

            state = "UP (recovered)" if is_up else "DOWN"

            now = time.strftime("%H:%M:%S")

            print(
                f"[LB {now}] {name} "
                f"({host}:{port}) is now {state}"
            )


def health_check_loop(stop_event):
    """Run health checks continuously in the background."""

    while not stop_event.wait(HEALTH_INTERVAL):

        check_all_backends()


def print_status():
    """Display current backend status."""

    for name, host, port in BACKENDS:

        state = (
            "UP" if scheduler.get_status(name)
            else "DOWN"
        )

        print(
            f"[LB] {name} -> {host}:{port} : {state}"
        )


# ==========================================
# 5. REQUEST FORWARDING
# ==========================================

def forward_request(backend, request):
    """Forward client request to the selected backend."""

    name, host, port = backend

    with socket.create_connection(
        (host, port),
        timeout=5
    ) as backend_sock:

        backend_sock.sendall(request.encode())

        return backend_sock.recv(1024).decode()


# ==========================================
# 6. CONCURRENT CLIENT REQUEST HANDLER
# ==========================================

def handle_client(client_conn, client_addr):

    global request_count

    with client_conn:

        request = client_conn.recv(1024).decode()

        if not request:
            return

        # Count the client request once
        with stats_lock:

            request_count += 1

            stats["total_requests"] += 1

            current_request = request_count

        attempted = set()

        response = "ERROR: no backend available"

        success = False

        while len(attempted) < len(BACKENDS):

            backend = scheduler.next_backend(attempted)

            if backend is None:
                break

            name = backend[0]

            # Count an additional backend attempt as a retry
            if attempted:

                with stats_lock:
                    stats["retries"] += 1

            attempted.add(name)

            try:

                response = forward_request(
                    backend,
                    request
                )

                with stats_lock:

                    stats["successful_requests"] += 1

                    stats["server_success"][name] += 1

                success = True

                print(
                    f"[LB] Request #{current_request} "
                    f"SUCCESS -> {name} | {request}"
                )

                break

            except OSError as error:

                # Mark failed backend as DOWN
                scheduler.set_status(name, False)

                with stats_lock:

                    stats["server_failures"][name] += 1

                response = (
                    "ERROR: all available backends failed"
                )

                print(
                    f"[LB] Request #{current_request} "
                    f"FAILED -> {name}: {error}"
                )

        if not success:

            with stats_lock:
                stats["failed_requests"] += 1

            print(
                f"[LB] Request #{current_request} "
                "could not be completed"
            )

        client_conn.sendall(response.encode())


# ==========================================
# 7. DISPLAY REQUEST STATISTICS
# ==========================================

def print_statistics():
    """Display final load balancer statistics."""

    with stats_lock:

        print("\n========== LOAD BALANCER STATISTICS ==========")

        print(
            "Total Requests:",
            stats["total_requests"]
        )

        print(
            "Successful Requests:",
            stats["successful_requests"]
        )

        print(
            "Failed Requests:",
            stats["failed_requests"]
        )

        print(
            "Retry Attempts:",
            stats["retries"]
        )

        print("\nBackend Statistics:")

        for name, _, _ in BACKENDS:

            print(
                f"{name}: "
                f"Successful = "
                f"{stats['server_success'][name]}, "
                f"Failed = "
                f"{stats['server_failures'][name]}"
            )

        print("==============================================\n")


# ==========================================
# 8. MAIN LOAD BALANCER
# ==========================================

def run_load_balancer():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((LB_HOST, LB_PORT))

    server.listen()

    print(
        f"[LB] Listening on {LB_HOST}:{LB_PORT}"
    )

    # Initial backend health check
    check_all_backends()

    print("\n[LB] Backend Status:")

    print_status()

    # Start background health checker
    stop_event = threading.Event()

    health_thread = threading.Thread(
        target=health_check_loop,
        args=(stop_event,),
        daemon=True
    )

    health_thread.start()

    # Keep track of client threads
    client_threads = []

    try:

        while True:

            client_conn, client_addr = server.accept()

            # Create a separate thread for each client
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_conn, client_addr),
                daemon=True
            )

            client_threads.append(client_thread)

            client_thread.start()

    except KeyboardInterrupt:

        print("\n[LB] Shutting down...")

    finally:

        stop_event.set()

        server.close()

        # Wait for active client threads to finish
        for thread in client_threads:

            thread.join()

        health_thread.join()

        # Display final statistics
        print_statistics()


# ==========================================
# 9. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    run_load_balancer()
