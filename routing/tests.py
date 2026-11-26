from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from routing.models import Edge, Node, RouteHistory


class NetworkRoutingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    # --- Node Tests ---

    def test_create_node_success(self):
        response = self.client.post("/nodes", {"name": "ServerA"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "ServerA")
        self.assertIn("id", response.data)

    def test_create_node_duplicate(self):
        self.client.post("/nodes", {"name": "ServerA"}, format="json")
        response = self.client.post("/nodes", {"name": "ServerA"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_node_missing_name(self):
        response = self.client.post("/nodes", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_empty = self.client.post("/nodes", {"name": ""}, format="json")
        self.assertEqual(response_empty.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_nodes(self):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerB")
        response = self.client.get("/nodes")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_delete_node(self):
        node = Node.objects.create(name="ServerA")
        response = self.client.delete(f"/nodes/{node.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Node.objects.filter(id=node.id).exists())

    def test_delete_node_not_found(self):
        response = self.client.delete("/nodes/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Edge Tests ---

    def test_create_edge_success(self):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerB")
        payload = {
            "source": "ServerA",
            "destination": "ServerB",
            "latency": 12.5,
        }
        response = self.client.post("/edges", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["source"], "ServerA")
        self.assertEqual(response.data["destination"], "ServerB")
        self.assertEqual(response.data["latency"], 12.5)

    def test_create_edge_duplicate_both_directions(self):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerB")
        payload1 = {"source": "ServerA", "destination": "ServerB", "latency": 12.5}
        self.assertEqual(self.client.post("/edges", payload1, format="json").status_code, status.HTTP_201_CREATED)

        # Same direction duplicate
        response_dup = self.client.post("/edges", payload1, format="json")
        self.assertEqual(response_dup.status_code, status.HTTP_400_BAD_REQUEST)

        # Reverse direction duplicate (undirected graph)
        payload_rev = {"source": "ServerB", "destination": "ServerA", "latency": 15.0}
        response_rev = self.client.post("/edges", payload_rev, format="json")
        self.assertEqual(response_rev.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_invalid_nodes(self):
        Node.objects.create(name="ServerA")
        payload = {"source": "ServerA", "destination": "ServerNonExistent", "latency": 10.0}
        response = self.client.post("/edges", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_invalid_latency(self):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerB")
        payload = {"source": "ServerA", "destination": "ServerB", "latency": 0.0}
        response = self.client.post("/edges", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload_neg = {"source": "ServerA", "destination": "ServerB", "latency": -5.0}
        response_neg = self.client.post("/edges", payload_neg, format="json")
        self.assertEqual(response_neg.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_edge_self_loop(self):
        Node.objects.create(name="ServerA")
        payload = {"source": "ServerA", "destination": "ServerA", "latency": 10.0}
        response = self.client.post("/edges", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_edges(self):
        a = Node.objects.create(name="ServerA")
        b = Node.objects.create(name="ServerB")
        Edge.objects.create(source=a, destination=b, latency=10.0)
        response = self.client.get("/edges")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_delete_edge(self):
        a = Node.objects.create(name="ServerA")
        b = Node.objects.create(name="ServerB")
        edge = Edge.objects.create(source=a, destination=b, latency=10.0)
        response = self.client.delete(f"/edges/{edge.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Edge.objects.filter(id=edge.id).exists())

    # --- Shortest Route Tests ---

    def test_shortest_route_success(self):
        # Network setup matching assignment example:
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
        response = self.client.post("/routes/shortest", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_latency"], 23.4)
        self.assertEqual(response.data["path"], ["ServerA", "ServerB", "ServerD"])

    def test_shortest_route_bidirectional_traversal(self):
        # Verify that undirected edge allows travel from destination back to source
        a = Node.objects.create(name="ServerA")
        b = Node.objects.create(name="ServerB")
        d = Node.objects.create(name="ServerD")

        Edge.objects.create(source=a, destination=b, latency=12.5)
        Edge.objects.create(source=b, destination=d, latency=10.9)

        payload = {"source": "ServerD", "destination": "ServerA"}
        response = self.client.post("/routes/shortest", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_latency"], 23.4)
        self.assertEqual(response.data["path"], ["ServerD", "ServerB", "ServerA"])

    def test_shortest_route_no_path_exists(self):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerIsolated")

        payload = {"source": "ServerA", "destination": "ServerIsolated"}
        response = self.client.post("/routes/shortest", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["error"], "No path exists between ServerA and ServerIsolated"
        )

    def test_shortest_route_non_existent_node(self):
        Node.objects.create(name="ServerA")
        payload = {"source": "ServerA", "destination": "ServerGhost"}
        response = self.client.post("/routes/shortest", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shortest_route_same_node(self):
        Node.objects.create(name="ServerA")
        payload = {"source": "ServerA", "destination": "ServerA"}
        response = self.client.post("/routes/shortest", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_latency"], 0.0)
        self.assertEqual(response.data["path"], ["ServerA"])

    # --- History Tests ---

    def test_history_records_successful_and_unreachable_queries(self):
        a = Node.objects.create(name="ServerA")
        b = Node.objects.create(name="ServerB")
        isolated = Node.objects.create(name="ServerIsolated")
        Edge.objects.create(source=a, destination=b, latency=12.5)

        # Successful route query (200 OK)
        self.client.post("/routes/shortest", {"source": "ServerA", "destination": "ServerB"}, format="json")

        # Unreachable route query (404 Not Found)
        self.client.post("/routes/shortest", {"source": "ServerA", "destination": "ServerIsolated"}, format="json")

        # History should have both entries
        response = self.client.get("/routes/history")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Most recent is the 404 entry (created_at desc)
        entry_404 = response.data[0]
        self.assertEqual(entry_404["source"], "ServerA")
        self.assertEqual(entry_404["destination"], "ServerIsolated")
        self.assertIsNone(entry_404["total_latency"])
        self.assertIsNone(entry_404["path"])

        # Earlier entry is the 200 entry
        entry_200 = response.data[1]
        self.assertEqual(entry_200["source"], "ServerA")
        self.assertEqual(entry_200["destination"], "ServerB")
        self.assertEqual(entry_200["total_latency"], 12.5)
        self.assertEqual(entry_200["path"], ["ServerA", "ServerB"])

    def test_history_filtering(self):
        RouteHistory.objects.create(source="ServerA", destination="ServerB", total_latency=10.0, path=["ServerA", "ServerB"])
        RouteHistory.objects.create(source="ServerB", destination="ServerC", total_latency=20.0, path=["ServerB", "ServerC"])
        RouteHistory.objects.create(source="ServerA", destination="ServerD", total_latency=30.0, path=["ServerA", "ServerD"])

        # Filter by source
        res_src = self.client.get("/routes/history?source=ServerA")
        self.assertEqual(len(res_src.data), 2)

        # Filter by destination
        res_dest = self.client.get("/routes/history?destination=ServerC")
        self.assertEqual(len(res_dest.data), 1)

        # Filter with limit
        res_limit = self.client.get("/routes/history?limit=1")
        self.assertEqual(len(res_limit.data), 1)
