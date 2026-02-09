from django.urls import path
from django.urls import path
from .views import (
    CreatePratoAPIView,
    CreateOrderAPIView,
    NextOrderAPIView,
    PainelCozinhaPratoView,
    FinalizarPratoView,
    PratoNextAPIView,
    IniciarPratoView,
)

urlpatterns = [
     # pratos
    path("pratos/", CreatePratoAPIView.as_view()),
    path("pratos/<uuid:prato_id>/next/", PratoNextAPIView.as_view()),
    


    # pedidos
    path("orders/", CreateOrderAPIView.as_view()),
    path("orders/next/", NextOrderAPIView.as_view()),

    # cozinha
    path("painel/prato/<uuid:prato_id>/", PainelCozinhaPratoView.as_view()),
    path("cozinha/finalizar/<uuid:fila_prato_id>/", FinalizarPratoView.as_view()),
    path("cozinha/iniciar/<uuid:fila_prato_id>/", IniciarPratoView.as_view()),

]
