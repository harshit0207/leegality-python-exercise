from collections import defaultdict
import heapq
from routing.models import Edge


def find_shortest_route(source, destination):
    """
    Basic Dijkstra implementation for undirected network graph.
    To be discussed and optimized.
    """
    if source == destination:
        return 0.0, [source]

    # Build undirected adjacency list
    graph = defaultdict(list)
    for edge in Edge.objects.select_related("source", "destination").all():
        u = edge.source.name
        v = edge.destination.name
        graph[u].append((v, edge.latency))
        graph[v].append((u, edge.latency))

    pq = [(0.0, source)]
    distances = {source: 0.0}
    previous = {}

    while pq:
        curr_dist, u = heapq.heappop(pq)

        if u == destination:
            break

        if curr_dist > distances.get(u, float("inf")):
            continue

        for v, weight in graph[u]:
            new_dist = curr_dist + weight
            if new_dist < distances.get(v, float("inf")):
                distances[v] = new_dist
                previous[v] = u
                heapq.heappush(pq, (new_dist, v))

    if destination not in distances:
        return None, None

    # Reconstruct path
    path = []
    curr = destination
    while curr != source:
        path.append(curr)
        curr = previous[curr]
    path.append(source)
    path.reverse()

    return round(distances[destination], 4), path
