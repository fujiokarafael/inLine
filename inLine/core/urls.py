from django.urls import path
from django.views.generic import TemplateView
from .views import (
    ListPratosAPIView, CreateOrderAPIView, 
    NextOrderAPIView, PainelCozinhaPratoView, 
    FinalizarPratoView,CreatePratoAPIView,
)

urlpatterns = [
    # TELAS (HTML) - Acesse exatamente com a barra no final
    path('caixa/', TemplateView.as_view(template_name="caixa.html"), name='gui-caixa'),
    path('atendimento/', TemplateView.as_view(template_name="atendimento.html"), name='gui-atendimento'),
    path('producao/', TemplateView.as_view(template_name="producao.html"), name='gui-producao'),
    path('cadastrar-prato/', TemplateView.as_view(template_name="cadastrar_prato.html"), name='gui-cadastrar'),

    # API - O JavaScript deve usar esse prefixo
    path('api/v1/pratos/', ListPratosAPIView.as_view()),
    path('api/v1/pratos/criar/', CreatePratoAPIView.as_view(), name='api_criar_prato'),
    path('api/v1/pedidos/criar/', CreateOrderAPIView.as_view()),
    path('api/v1/fila/proximo/', NextOrderAPIView.as_view(), name='proximo_pedido'),
    path('api/v1/fila/painel/', PainelCozinhaPratoView.as_view(), name='painel-cozinha'),
    path('api/v1/fila/finalizar/<uuid:id>/', FinalizarPratoView.as_view(), name='finalizar-prato'),
    
]