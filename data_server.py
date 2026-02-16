import json
import socket

# load listings
with open("listings.json", "r") as file:
    listings = json.load(file)

# format listings
def format(listings):
    formated_listing = ""
    for listing in listings:
        formated_listing += (f"id=<{listing["id"]}>;city=<{listing["city"]}>;address=<{listing["address"]}>;price=<{listing["price"]}>;bedrooms=<{listing["bedrooms"]}>")
    
    formated_listing += "\n"
    return formated_listing

# Raw search city and price
def r_search(listings, city, max_price):
    r_search = []
    for listing in listings:
        if listing["city"] == city and listing["price"] <= max_price:
            r_search.append(listing)
  
    return r_search


HOST = '127.0.0.1'
PORT = 50001

def handle_app(conn, addr):
    print("Connected by", addr)
    with conn:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            text = data.decode('utf-8').strip()
            details = text.split()
            #check message if its valid
            if details[0] == "RAW_LIST":
                conn.sendall(format(listings).encode("utf-8"))

            elif details[0] == "RAW_SEARCH":
                info = details[1:]
                search_params = {}

                try:
                    for i in info:
                        key, val = i.split("=")
                        search_params[key] = val
                    
                    search_params["max_price"] = int(search_params["max_price"])
                    conn.sendall(format(r_search(listings, search_params["city"], search_params["max_price"])).encode("utf-8"))

                except Exception as e:
                    conn.sendall(f"Error: {e}\n".encode("utf-8"))
            else:
                conn.sendall("Error: Invalid Command")
    print("Disconnected", addr)

def main():
    # create a socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_server:

        data_server.bind((HOST, PORT))
        data_server.listen()

        # sequentially recieve message
        while True:
            conn, addr = data_server.accept()
            handle_app(conn, addr)
