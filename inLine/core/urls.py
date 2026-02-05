from django.urls import path
from .views import CreateOrderAPIView, NextOrderAPIView

urlpatterns = [
    path("orders/", CreateOrderAPIView.as_view()),
    path("orders/next/", NextOrderAPIView.as_view()),
]
