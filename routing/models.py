from django.db import models


class Node(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Edge(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing")
    destination = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming")
    latency = models.FloatField()

    def __str__(self):
        return f"{self.source.name} - {self.destination.name} ({self.latency})"


class RouteHistory(models.Model):
    source = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    total_latency = models.FloatField(null=True, blank=True)
    path = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
