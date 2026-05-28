from django.urls import path
from django.views.generic import TemplateView
from .views import (
    ListPratosAPIView, CreateOrderAPIView, 
    PainelCozinhaPratoView, 
    FinalizarPratoView,CreatePratoAPIView, TMADashboardAPIView,
    AcompanhamentoPedidoView,DashboardView, MonitorPedidosView, MonitorPedidosAPIView,
    RetirarPedidoView,BaixaEntregaView,UpdatePratoAPIView, 
    PainelQuantitativoProducaoAPIView,AtendimentoListaAPIView, PainelPorPratoView, IniciarPratoView,ExpedicaoPedidosAPIView,ExpedicaoPainelView,
)

urlpatterns = [
    # TELAS (HTML) - Acesse exatamente com a barra no final
    path('caixa/', TemplateView.as_view(template_name="caixa.html"), name='gui-caixa'),
    path('atendimento/', TemplateView.as_view(template_name="atendimento.html"), name='gui-atendimento'),
    path('producao/', TemplateView.as_view(template_name="producao.html"), name='gui-producao'),
    path('cadastrar-prato/', TemplateView.as_view(template_name="cadastrar_prato.html"), name='gui-cadastrar'),
    path('', DashboardView.as_view(), name='dashboard-central'), # Home do sistema,
    path('acompanhamento/<str:pedido_id>/', AcompanhamentoPedidoView.as_view(), name='acompanhamento_pedido'),
    path('monitor/', MonitorPedidosView.as_view(), name='monitor-cliente'),
    path('atendimento/baixa-entrega/', BaixaEntregaView.as_view(), name='gui-baixa-entrega'),
    path('producao/painel/', TemplateView.as_view(template_name='painel_producao.html'), name='painel-producao'),
    path('api/v1/atendimento/lista/', AtendimentoListaAPIView.as_view(), name='atendimento-lista'),
    path('producao/painel/<str:id>/', PainelPorPratoView.as_view(), name='painel-por-prato'),
    path('producao/expedicao/', ExpedicaoPainelView.as_view(), name='painel-expedicao'),    

    # API - O JavaScript deve usar esse prefixo
    path('api/v1/pratos/', ListPratosAPIView.as_view()),
    path('api/v1/pratos/criar/', CreatePratoAPIView.as_view(), name='api_criar_prato'),
    path('api/v1/pedidos/criar/', CreateOrderAPIView.as_view()),
    path('api/v1/fila/proximo/', AtendimentoListaAPIView.as_view(), name='proximo_pedido'),
    path('api/v1/fila/painel/', PainelCozinhaPratoView.as_view(), name='painel-cozinha'),
    path('api/v1/fila/<str:id>/finalizar/', FinalizarPratoView.as_view(), name='api-finalizar-prato'),
    path('api/v1/metrica/tma-dashboard/', TMADashboardAPIView.as_view(), name='tma'),
    path('api/v1/monitor/pedidos/', MonitorPedidosAPIView.as_view(), name='api-monitor-pedidos'),
    path('api/v1/pedidos/retirar/<uuid:pedido_id>/', RetirarPedidoView.as_view(), name='retirar-pedido'),   
    path('api/v1/pratos/editar/<uuid:prato_id>/', UpdatePratoAPIView.as_view(), name='editar-prato'),
    path('api/v1/producao/quantitativo/', PainelQuantitativoProducaoAPIView.as_view()),
    path('api/v1/atendimento/lista/<uuid:pedido_id>/', AtendimentoListaAPIView.as_view(), name='atendimento-acao'),
    path('api/v1/fila/<str:id>/iniciar/', IniciarPratoView.as_view(), name='api-iniciar-prato'),
    path('api/v1/monitor/pedidos/', ExpedicaoPedidosAPIView.as_view(), name='api-expedicao-monitor'),
    ] 