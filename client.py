import socket
import sys
import time

APP_SERVER_HOST = '127.0.0.1'
APP_SERVER_PORT = 8001


def send_command(sock, command):
    """"Sends a command and returns the full response string."""
    sock.sendall((command + "\n").encode())

    response = ""
    while True:
        chunk = sock.recv(4096).decode()
        if not chunk: break
        response += chunk
        if "END\n" in response: break
    return response


def print_table(response):
    """Parses the protocol response and prints a pretty table."""
    lines = response.split('\n')
    if not lines[0].startswith("OK"):
        print(f"Server Error: {lines[0]}")
        return

    print(f"\n{'ID':<5} {'City':<15} {'Price':<10} {'Beds':<5}")
    print("-" * 65)

    for line in lines:
        if "id=" not in line: continue

        # string parsing
        parts = line.split(';')
        data = {}
        for p in parts:
            k, v = p.split('=')
            data[k] = v

        print(f"{data['id']:<5} {data['city']:<15} {data['address']:<25} ${data['price']:<9} {data['bedrooms']:<5}")
    print("\n")


def run_benchmark():
    """Runs the performance experiment (50 requests)."""
    print("\n--- Starting Benchmark (50 Requests) ---")
    cmd = "Search city=LongBeach max_price=3000"

    start_time = time.time()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((APP_SERVER_HOST, APP_SERVER_PORT))

            for i in range(50):
                send_command(s, cmd)
                # optional: print a dot for progress
                print(".", end="", flush=True)

    except Exception as e:
        print(f"Benchmark failed: {e}")
        return
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / 50

    print(f"\n\nTotal Time: {total_time:.4f} seconds")
    print(f"Average Time per Request: {avg_time:.4f} seconds")
    print("----------------------------------------")


def main():
    if "--benchmark" in sys.argv:
        run_benchmark()
        return

    print("Connecting to Housing Server...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((APP_SERVER_HOST, APP_SERVER_PORT))
    except ConnectionRefusedError:
        print("Error:Could not connect to Application Server.")
        return

    print("Welcome! commands: SEARCH, LIST, QUIT")

    while True:
        try:
            user_input = input(">> ").strip()

            if not user_input: continue

            if user_input.upper() == "QUIT":
                sock.sendall("QUIT\n".encode())
                break

            if user_input.upper().startswith("SEARCH") and "=" not in user_input:
                city = input("Enter City: ")
                price = input("Enter Max Price: ")
                command = f"SEARCH city={city} max_price={price}"

            else:
                command = user_input

            response = send_command(sock, command)
            print_table(response)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            break

    sock.close()
    print("Goodbye!")


if __name__ == '__main__':
    main()
