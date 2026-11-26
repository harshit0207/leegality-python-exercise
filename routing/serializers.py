from rest_framework import serializers

from routing.models import Edge, Node, RouteHistory


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ["id", "name"]


class EdgeSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(slug_field="name", queryset=Node.objects.all())
    destination = serializers.SlugRelatedField(slug_field="name", queryset=Node.objects.all())

    class Meta:
        model = Edge
        fields = ["id", "source", "destination", "latency"]

    def validate_latency(self, value):
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0")
        return value

    def validate(self, data):
        source = data.get("source")
        destination = data.get("destination")

        if source == destination:
            raise serializers.ValidationError("Source and destination cannot be the same node")

        # Undirected check: check if edge exists as A->B or B->A
        if Edge.objects.filter(source=source, destination=destination).exists() or \
           Edge.objects.filter(source=destination, destination=source).exists():
            raise serializers.ValidationError("Duplicate edge exists between these nodes")

        return data


class RouteHistorySerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = RouteHistory
        fields = ["id", "source", "destination", "total_latency", "path", "created_at"]
