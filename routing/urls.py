from django.urls import re_path
from routing import views

urlpatterns = [
    re_path(r"^nodes/?$", views.NodeListCreateView.as_view(), name="nodes-list-create"),
    re_path(r"^nodes/(?P<pk>\d+)/?$", views.NodeDetailView.as_view(), name="nodes-detail"),
    re_path(r"^edges/?$", views.EdgeListCreateView.as_view(), name="edges-list-create"),
    re_path(r"^edges/(?P<pk>\d+)/?$", views.EdgeDetailView.as_view(), name="edges-detail"),
    re_path(r"^routes/shortest/?$", views.ShortestRouteView.as_view(), name="shortest-route"),
    re_path(r"^routes/history/?$", views.RouteHistoryView.as_view(), name="routes-history"),
]
