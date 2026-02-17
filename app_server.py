import socket
import time
import re
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional

APP_HOST = "127.0.0.1"
APP_PORT = 8001

DATA_HOST = "127.0.0.1"
DATA_PORT = 49963

LOG_FILE = "app_server.log"

# cache: True to enable caching, False to disable
CACHE_ENABLED = True
CACHE_MAX_ITEMS = 20

# logging interceptor
def log_line(text: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {text}\n")

def log_request(client_addr: Tuple[str, int], request: str) -> None:
    log_line(f"CLIENT {client_addr[0]}:{client_addr[1]} -> {request}")

def log_reply(client_addr: Tuple[str, int], reply: str, cache_hit: bool) -> None:
    first = reply.splitlines()[0] if reply else ""
    log_line(f"SERVER -> CLIENT {client_addr[0]}:{client_addr[1]} (cache_hit={cache_hit}) :: {first}")

def log_ads(request: str, response_first_line: str) -> None:
    log_line(f"APP -> DATA :: {request} || DATA -> APP :: {response_first_line}")

# CAS protocol helpers
def cas_error(msg: str) -> str:
    return f"ERROR {msg}\nEND\n"

def cas_ok(listings: List[Dict]) -> str:
    lines = [f"OK RESULT {len(listings)}"]
    for li in listings:
        lines.append(
            f"id={li['id']};city={li['city']};address={li['address']};price={li['price']};bedrooms={li['bedrooms']}"
        )
    lines.append("END")
    return "\n".join(lines) + "\n"

def canonical_cache_key(command_line: str) -> str:
    cmd = command_line.strip()
    if not cmd:
        return ""

    parts = cmd.split()
    head = parts[0].upper()
    if head == "LIST":
        return "LIST"
    if head == "QUIT":
        return "QUIT"
    if head == "SEARCH":
        kv = {}
        for token in parts[1:]:
            if "=" in token:
                k, v = token.split("=", 1)
                kv[k.strip().lower()] = v.strip()
        city = kv.get("city", "")
        maxp = kv.get("max_price", "")
        return f"SEARCH city={city} max_price={maxp}"
    return head + (" " + " ".join(parts[1:]) if len(parts) > 1 else "")

def parse_search_params(command_line: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    parts = command_line.strip().split()
    if len(parts) < 3:
        return None, None, "invalid SEARCH syntax (expected: SEARCH city=<City> max_price=<Int>)"

    kv = {}
    for token in parts[1:]:
        if "=" not in token:
            return None, None, "invalid SEARCH syntax (expected key=value fields)"
        k, v = token.split("=", 1)
        kv[k.strip().lower()] = v.strip()

    if "city" not in kv or "max_price" not in kv:
        return None, None, "SEARCH requires city and max_price"

    city = kv["city"]
    try:
        max_price = int(kv["max_price"])
    except ValueError:
        return None, None, "max_price must be an integer"

    return city, max_price, None

# data server
def recv_all_with_timeout(sock: socket.socket, timeout_s: float = 0.25) -> str:
    sock.settimeout(timeout_s)
    chunks = []
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            chunks.append(data.decode("utf-8", errors="replace"))
            if "END\n" in chunks[-1] or "END\r\n" in chunks[-1]:
                break
        except socket.timeout:
            break
    return "".join(chunks)

def query_data_server(request_line: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((DATA_HOST, DATA_PORT))
        s.sendall((request_line.strip() + "\n").encode("utf-8"))
        resp = recv_all_with_timeout(s)
        first = resp.splitlines()[0] if resp else ""
        log_ads(request_line.strip(), first)
        return resp

# ADS protocol response into list of dicts
LISTING_RE = re.compile(
    r"id\s*=\s*<?(?P<id>\d+)>?\s*;"
    r"\s*city\s*=\s*<?(?P<city>[^;<>]+)>?\s*;"
    r"\s*address\s*=\s*<?(?P<address>[^;<>]+)>?\s*;"
    r"\s*price\s*=\s*<?(?P<price>\d+)>?\s*;"
    r"\s*bedrooms\s*=\s*<?(?P<bedrooms>\d+)>?",
    re.IGNORECASE,
)

def parse_ads_response(raw: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    if not raw:
        return None, "no response from data server"

    first = raw.splitlines()[0].strip() if raw.splitlines() else raw.strip()
    if first.upper().startswith("ERROR") or first.lower().startswith("error"):
        msg = first.split(" ", 1)[1] if " " in first else "data server error"
        return None, msg

    if not first.upper().startswith("OK RESULT"):
        return None, "unexpected response from data server"

    listings: List[Dict] = []
    for m in LISTING_RE.finditer(raw):
        listings.append({
            "id": int(m.group("id")),
            "city": m.group("city").strip(),
            "address": m.group("address").strip(),
            "price": int(m.group("price")),
            "bedrooms": int(m.group("bedrooms")),
        })

    if "OK RESULT" in first.upper():
        try:
            n = int(first.split()[-1])
            if n > 0 and not listings:
                return None, "could not parse listings from data server response"
        except Exception:
            pass

    return listings, None

# rank: price ascending, bedrooms decending
def rank_listings(listings: List[Dict]) -> List[Dict]:
    return sorted(listings, key=lambda x: (x["price"], -x["bedrooms"]))

# lru cache
class LRUCache:
    def __init__(self, max_items: int):
        self.max_items = max_items
        self.od = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        if key in self.od:
            self.od.move_to_end(key)
            return self.od[key]
        return None

    def put(self, key: str, value: str) -> None:
        self.od[key] = value
        self.od.move_to_end(key)
        if len(self.od) > self.max_items:
            self.od.popitem(last=False)

CACHE = LRUCache(CACHE_MAX_ITEMS)

# client handling
def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    with conn:
        buf = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data.decode("utf-8", errors="replace")

            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                log_request(addr, line)

                parts = line.split()
                cmd = parts[0].upper()

                if cmd == "QUIT":
                    reply = "OK RESULT 0\nEND\n"
                    conn.sendall(reply.encode("utf-8"))
                    log_reply(addr, reply, cache_hit=False)
                    return

                if cmd not in ("LIST", "SEARCH"):
                    reply = cas_error("invalid command (use LIST, SEARCH, or QUIT)")
                    conn.sendall(reply.encode("utf-8"))
                    log_reply(addr, reply, cache_hit=False)
                    continue

                # caching
                key = canonical_cache_key(line)
                cache_hit = False

                if CACHE_ENABLED:
                    cached = CACHE.get(key)
                    if cached is not None:
                        cache_hit = True
                        conn.sendall(cached.encode("utf-8"))
                        log_reply(addr, cached, cache_hit=True)
                        continue

                # not in cache
                if cmd == "LIST":
                    raw = query_data_server("RAW_LIST")
                    listings, err = parse_ads_response(raw)
                    if err:
                        reply = cas_error(err)
                    else:
                        ranked = rank_listings(listings or [])
                        reply = cas_ok(ranked)

                else:  # SEARCH
                    city, max_price, err = parse_search_params(line)
                    if err:
                        reply = cas_error(err)
                    else:
                        raw = query_data_server(f"RAW_SEARCH city={city} max_price={max_price}")
                        listings, derr = parse_ads_response(raw)
                        if derr:
                            reply = cas_error(derr)
                        else:
                            ranked = rank_listings(listings or [])
                            reply = cas_ok(ranked)

                if CACHE_ENABLED and cmd in ("LIST", "SEARCH") and reply.startswith("OK"):
                    CACHE.put(key, reply)

                conn.sendall(reply.encode("utf-8"))
                log_reply(addr, reply, cache_hit=cache_hit)

def main():
    log_line(f"=== app_server starting on {APP_HOST}:{APP_PORT}, DATA={DATA_HOST}:{DATA_PORT}, CACHE_ENABLED={CACHE_ENABLED} ===")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((APP_HOST, APP_PORT))
        server.listen()
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)

if __name__ == "__main__":
    main()