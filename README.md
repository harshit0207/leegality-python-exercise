# Network Route Optimization API

A simplified, production-ready Django REST Framework service for network topology management and shortest-path route calculation.

---

## Running with Docker (No local venv needed)

### 1. Build and Start the Application
```bash
docker compose up --build
```
The server will start at `http://127.0.0.1:8000`.
Migrations are executed automatically on container startup.

### 2. Run Tests with pytest inside Docker
```bash
docker compose run --rm web pytest
```

*(Or using standard Django test runner)*:
```bash
docker compose run --rm web python manage.py test routing
```

### 3. Stop the Containers
```bash
docker compose down
```

---

## API Specification

### 1. Add Node
- **`POST /nodes`**
  ```json
  { "name": "ServerA" }
  ```
  Returns `201 Created` (`{"id": 1, "name": "ServerA"}`). Rejects empty or duplicate names with `400 Bad Request`.
- **`GET /nodes`**: Lists all nodes (`200 OK`).
- **`DELETE /nodes/{id}`**: Deletes a node (`204 No Content`).

### 2. Add Edge
- **`POST /edges`**
  ```json
  { "source": "ServerA", "destination": "ServerB", "latency": 12.5 }
  ```
  Returns `201 Created`. Rejects missing nodes, self-loops, latency $\le 0$, and duplicates in either direction with `400 Bad Request`.
- **`GET /edges`**: Lists all edges (`200 OK`).
- **`DELETE /edges/{id}`**: Deletes an edge (`204 No Content`).

### 3. Get Shortest Route
- **`POST /routes/shortest`**
  ```json
  { "source": "ServerA", "destination": "ServerD" }
  ```
  Returns `200 OK` (`{"total_latency": 23.4, "path": ["ServerA", "ServerB", "ServerD"]}`).
  Returns `404 Not Found` if no path exists (`{"error": "No path exists between ServerA and ServerD"}`).

### 4. Route Query History
- **`GET /routes/history`**
  - Optional query parameters: `source`, `destination`, `limit`, `date_from`, `date_to`.
  - Returns `200 OK` with history list.

---

## Quick Testing with cURL

```bash
# 1. Create nodes
curl -s -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name": "ServerA"}'
curl -s -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name": "ServerB"}'
curl -s -X POST http://127.0.0.1:8000/nodes -H "Content-Type: application/json" -d '{"name": "ServerD"}'

# 2. Create edges
curl -s -X POST http://127.0.0.1:8000/edges -H "Content-Type: application/json" -d '{"source": "ServerA", "destination": "ServerB", "latency": 12.5}'
curl -s -X POST http://127.0.0.1:8000/edges -H "Content-Type: application/json" -d '{"source": "ServerB", "destination": "ServerD", "latency": 10.9}'

# 3. Find shortest route
curl -s -X POST http://127.0.0.1:8000/routes/shortest -H "Content-Type: application/json" -d '{"source": "ServerA", "destination": "ServerD"}'

# 4. View history
curl -s http://127.0.0.1:8000/routes/history
```
