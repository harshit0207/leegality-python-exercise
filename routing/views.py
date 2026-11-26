from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.models import Edge, Node, RouteHistory
from routing.serializers import EdgeSerializer, NodeSerializer, RouteHistorySerializer
from routing.services import find_shortest_route


class NodeListCreateView(APIView):
    def post(self, request):
        serializer = NodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        nodes = Node.objects.all()
        return Response(NodeSerializer(nodes, many=True).data)


class NodeDetailView(APIView):
    def delete(self, request, pk):
        try:
            node = Node.objects.get(pk=pk)
            node.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Node.DoesNotExist:
            return Response({"error": "Node not found"}, status=status.HTTP_404_NOT_FOUND)


class EdgeListCreateView(APIView):
    def post(self, request):
        serializer = EdgeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        edges = Edge.objects.all()
        return Response(EdgeSerializer(edges, many=True).data)


class EdgeDetailView(APIView):
    def delete(self, request, pk):
        try:
            edge = Edge.objects.get(pk=pk)
            edge.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Edge.DoesNotExist:
            return Response({"error": "Edge not found"}, status=status.HTTP_404_NOT_FOUND)


class ShortestRouteView(APIView):
    def post(self, request):
        source = request.data.get("source")
        destination = request.data.get("destination")

        if not source or not destination:
            return Response({"error": "Source and destination are required"}, status=status.HTTP_400_BAD_REQUEST)

        if not Node.objects.filter(name=source).exists() or not Node.objects.filter(name=destination).exists():
            return Response({"error": "Invalid or non-existent nodes"}, status=status.HTTP_400_BAD_REQUEST)

        total_latency, path = find_shortest_route(source, destination)

        # Record query history (both successful and failed attempts)
        RouteHistory.objects.create(
            source=source,
            destination=destination,
            total_latency=total_latency,
            path=path,
        )

        if path is not None:
            return Response({"total_latency": total_latency, "path": path}, status=status.HTTP_200_OK)
        return Response({"error": f"No path exists between {source} and {destination}"}, status=status.HTTP_404_NOT_FOUND)


class RouteHistoryView(APIView):
    def get(self, request):
        queryset = RouteHistory.objects.all()

        source = request.query_params.get("source")
        if source:
            queryset = queryset.filter(source=source)

        destination = request.query_params.get("destination")
        if destination:
            queryset = queryset.filter(destination=destination)

        date_from = request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        limit = request.query_params.get("limit")
        if limit and limit.isdigit():
            queryset = queryset[:int(limit)]

        return Response(RouteHistorySerializer(queryset, many=True).data)
