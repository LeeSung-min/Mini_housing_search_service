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
                print(format(listings))
            elif details[0] == "RAW_SEARCH":
                pass
            else:
                print("Error: Invalid Command")
    print("Disconnected", addr)


print("RAW_List")
print(format(listings))
print("\nSearch ")
print(format(r_search(listings, "LongBeach", 2200)))

