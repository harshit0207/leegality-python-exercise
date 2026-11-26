import pytest
from rest_framework import status
from rest_framework.test import APIClient

from routing.models import Edge, Node, RouteHistory


@pytest.fixture
def client():
    return APIClient()


# ---------------------------------------------------------------------------
# Node API Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_node_success(client):
    response = client.post("/nodes", {"name": "ServerA"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "ServerA"
    assert "id" in response.data


@pytest.mark.django_db
def test_create_node_duplicate(client):
    client.post("/nodes", {"name": "ServerA"}, format="json")
    response = client.post("/nodes", {"name": "ServerA"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_node_empty_or_missing_name(client):
    response_missing = client.post("/nodes", {}, format="json")
    assert response_missing.status_code == status.HTTP_400_BAD_REQUEST

    response_empty = client.post("/nodes", {"name": ""}, format="json")
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_nodes(client):
    Node.objects.create(name="ServerA")
    Node.objects.create(name="ServerB")
    response = client.get("/nodes")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


@pytest.mark.django_db
def test_delete_node_success(client):
    node = Node.objects.create(name="ServerA")
    response = client.delete(f"/nodes/{node.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Node.objects.filter(id=node.id).exists()


@pytest.mark.django_db
def test_delete_node_not_found(client):
    response = client.delete("/nodes/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Edge API Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_edge_success(client):
    Node.objects.create(name="ServerA")
    Node.objects.create(name="ServerB")
    payload = {"source": "ServerA", "destination": "ServerB", "latency": 12.5}
    response = client.post("/edges", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["source"] == "ServerA"
    assert response.data["destination"] == "ServerB"
    assert response.data["latency"] == 12.5


@pytest.mark.django_db
def test_create_edge_duplicate_both_directions(client):
    Node.objects.create(name="ServerA")
    Node.objects.create(name="ServerB")
    payload = {"source": "ServerA", "destination": "ServerB", "latency": 12.5}
    assert client.post("/edges", payload, format="json").status_code == status.HTTP_201_CREATED

    # Duplicate in same direction
    dup_forward = client.post("/edges", payload, format="json")
    assert dup_forward.status_code == status.HTTP_400_BAD_REQUEST

    # Duplicate in reverse direction (undirected graph)
    dup_reverse = client.post("/edges", {"source": "ServerB", "destination": "ServerA", "latency": 15.0}, format="json")
    assert dup_reverse.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_edge_non_existent_node(client):
    Node.objects.create(name="ServerA")
    payload = {"source": "ServerA", "destination": "ServerGhost", "latency": 10.0}
    response = client.post("/edges", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_edge_invalid_latency(client):
    Node.objects.create(name="ServerA")
    Node.objects.create(name="ServerB")
    for invalid_latency in [0.0, -5.0]:
        payload = {"source": "ServerA", "destination": "ServerB", "latency": invalid_latency}
        response = client.post("/edges", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_edge_self_loop(client):
    Node.objects.create(name="ServerA")
    payload = {"source": "ServerA", "destination": "ServerA", "latency": 10.0}
    response = client.post("/edges", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_edges(client):
    a = Node.objects.create(name="ServerA")
    b = Node.objects.create(name="ServerB")
    Edge.objects.create(source=a, destination=b, latency=10.0)
    response = client.get("/edges")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_delete_edge_success(client):
    a = Node.objects.create(name="ServerA")
    b = Node.objects.create(name="ServerB")
    edge = Edge.objects.create(source=a, destination=b, latency=10.0)
    response = client.delete(f"/edges/{edge.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Edge.objects.filter(id=edge.id).exists()


@pytest.mark.django_db
def test_delete_edge_not_found(client):
    response = client.delete("/edges/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Shortest Route API Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_shortest_route_success(client):
    # Matches assignment diagram:
    # ServerA --(12.5)--> ServerB --(10.9)--> ServerD (Total: 23.4)
    # ServerA --(20.0)--> ServerC --(15.0)--> ServerD (Total: 35.0)
    a = Node.objects.create(name="ServerA")
    b = Node.objects.create(name="ServerB")
    c = Node.objects.create(name="ServerC")
    d = Node.objects.create(name="ServerD")

    Edge.objects.create(source=a, destination=b, latency=12.5)
    Edge.objects.create(source=b, destination=d, latency=10.9)
    Edge.objects.create(source=a, destination=c, latency=20.0)
    Edge.objects.create(source=c, destination=d, latency=15.0)

    payload = {"source": "ServerA", "destination": "ServerD"}
    response = client.post("/routes/shortest", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_latency"] == 23.4
    assert response.data["path"] == ["ServerA", "ServerB", "ServerD"]


@pytest.mark.django_db
def test_shortest_route_bidirectional_traversal(client):
    a = Node.objects.create(name="ServerA")
    b = Node.objects.create(name="ServerB")
    d = Node.objects.create(name="ServerD")

    Edge.objects.create(source=a, destination=b, latency=12.5)
    Edge.objects.create(source=b, destination=d, latency=10.9)

    payload = {"source": "ServerD", "destination": "ServerA"}
    response = client.post("/routes/shortest", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_latency"] == 23.4
    assert response.data["path"] == ["ServerD", "ServerB", "ServerA"]


@pytest.mark.django_db
def test_shortest_route_same_node(client):
    Node.objects.create(name="ServerA")
    payload = {"source": "ServerA", "destination": "ServerA"}
    response = client.post("/routes/shortest", payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_latency"] == 0.0
    assert response.data["path"] == ["ServerA"]


@pytest.mark.django_db
def test_shortest_route_no_path_exists(client):
    Node.objects.create(name="ServerA")
    Node.objects.create(name="ServerIsolated")

    payload = {"source": "ServerA", "destination": "ServerIsolated"}
    response = client.post("/routes/shortest", payload, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["error"] == "No path exists between ServerA and ServerIsolated"


@pytest.mark.django_db
def test_shortest_route_non_existent_node(client):
    Node.objects.create(name="ServerA")
    payload = {"source": "ServerA", "destination": "ServerGhost"}
    response = client.post("/routes/shortest", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_shortest_route_missing_parameters(client):
    response = client.post("/routes/shortest", {"source": "ServerA"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Route Query History API Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_history_records_both_200_and_404(client):
    a = Node.objects.create(name="ServerA")
    b = Node.objects.create(name="ServerB")
    isolated = Node.objects.create(name="ServerIsolated")
    Edge.objects.create(source=a, destination=b, latency=12.5)

    # 1. Successful query (200 OK)
    client.post("/routes/shortest", {"source": "ServerA", "destination": "ServerB"}, format="json")

    # 2. Failed query (404 Not Found)
    client.post("/routes/shortest", {"source": "ServerA", "destination": "ServerIsolated"}, format="json")

    # Retrieve history
    response = client.get("/routes/history")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2

    # Most recent entry is the 404 query
    entry_404 = response.data[0]
    assert entry_404["source"] == "ServerA"
    assert entry_404["destination"] == "ServerIsolated"
    assert entry_404["total_latency"] is None
    assert entry_404["path"] is None

    # Previous entry is the 200 query
    entry_200 = response.data[1]
    assert entry_200["source"] == "ServerA"
    assert entry_200["destination"] == "ServerB"
    assert entry_200["total_latency"] == 12.5
    assert entry_200["path"] == ["ServerA", "ServerB"]


@pytest.mark.django_db
def test_history_filtering_and_limit(client):
    RouteHistory.objects.create(source="ServerA", destination="ServerB", total_latency=10.0, path=["ServerA", "ServerB"])
    RouteHistory.objects.create(source="ServerB", destination="ServerC", total_latency=20.0, path=["ServerB", "ServerC"])
    RouteHistory.objects.create(source="ServerA", destination="ServerD", total_latency=30.0, path=["ServerA", "ServerD"])

    # Filter by source
    res_src = client.get("/routes/history?source=ServerA")
    assert len(res_src.data) == 2

    # Filter by destination
    res_dest = client.get("/routes/history?destination=ServerC")
    assert len(res_dest.data) == 1

    # Limit
    res_limit = client.get("/routes/history?limit=1")
    assert len(res_limit.data) == 1
