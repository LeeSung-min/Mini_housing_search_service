# Mini Housing Search Service

A three-tier distributed system built to simulate an online housing search engine (like Zillow). This project demonstrates the separation of concerns between data storage, application logic, and user interface using TCP socket programming.

## 1. System Architecture
This project follows a **Three-Tier Architecture**:
* **Presentation Layer (`client.py`)**: A command-line interface that allows users to search by city and price or list all entries.
* **Application Layer (`app_server.py`)**: Handles the "business logic." It parses queries, manages a cache of recent results, implements an interceptor for logging, and ranks/filters data.
* **Data Layer (`data_server.py`)**: Manages the `listings.json` file and handles raw data requests from the Application Server.



---

## 2. Setup & Installation

### Prerequisites
* Python 3.x
* Ensure all three files (`client.py`, `app_server.py`, `data_server.py`) and the data file (`listings.json`) are in the same directory.

### Configuration
* **Data Server Port**: 5001 (Default)
* **Application Server Port**: 5000 (Default)
* **Logging**: All traffic is recorded in `app_server.log`.

---

## 3. How to Run
To run the system, open **three separate terminals** and execute the commands in this specific order:

1. **Start the Data Server**:
   python data_server.py
   
2. **Start the Application Server**:
    python app_server.py
3. **Start the Client**:
    python client.py

### 4. Communication Protocol
The system uses a custom text-based protocol over TCP:

Client <-> App Server
SEARCH city=<CityName> max_price=<Integer>: Returns filtered and ranked results.

LIST: Returns all available listings.

QUIT: Gracefully closes the connection.

App Server <-> Data Server
RAW_SEARCH city=<CityName> max_price=<Integer>: App Server requests raw filtered data.

RAW_LIST: App Server requests all entries from the JSON database

### 5. Key Features
Caching: The Application Server stores recent query results. If a user repeats a search, the server serves the result from memory instead of querying the Data Server.

Ranking: Results are sorted by Price (Ascending) and Bedrooms (Descending).

Logging Interceptor: Every request and reply handled by the Application Server is written to app_server.log.

Layering: The client never communicates with the Data Server directly, ensuring strict distribution transparency.

### 6. Performance Experiment
We conducted a scalability test by running the same SEARCH command 50 times.

Without Caching: High latency due to repeated network hops and disk I/O at the Data Server.

With Caching: Significant speedup as the Application Server provides "instant" responses from memory after the first request.

### 7. Team Contributions
[Caleb Lee]: Developed data_server.py and handled JSON data management.

[Anthony Tieu]: Developed app_server.py, including caching logic and the logging interceptor.

[Beau Cordero]: Developed client.py, conducted performance experiments, and authored the README and PDF Report.
