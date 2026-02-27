
from django.db.models import Count, Avg, F, ExpressionWrapper, fields, Q
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .services import (
    create_order,
    finalize_prato,
)
from .models import Pedido, FilaPrato, Prato, TMA

class CreatePratoAPIView(APIView):
    def post(self, request):
        nome = request.data.get("nome")
        preco = request.data.get("preco")
        # O front pode enviar como 'tempo_preparo_seg' ou 'tempo'
        tempo = request.data.get("tempo_preparo_seg") or request.data.get("tempo")

        if not nome or not preco:
            return Response({"error": "Nome e preço são obrigatórios"}, status=400)

        try:
            prato = Prato.objects.create(
                nome=nome,
                preco=preco,
                tempo_preparo_seg=int(tempo) if tempo else 300,
                ativo=True
            )
            return Response({"id": str(prato.id), "status": "salvo"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# =========================
# CRIAR PEDIDO
# =========================

class CreateOrderAPIView(APIView):
    def post(self, request):
        # Captura os dados enviados pelo JavaScript
        tipo = request.data.get("tipo")
        itens = request.data.get("itens", [])
        
        try:
            # Chama o service que cria o pedido e os itens da fila (FilaPrato)
            pedido = create_order(tipo=tipo, itens=itens)
            
            # Identifica o host (IP local ou URL do Codespaces)
            host = request.get_host() 
            status_url = f"http://{host}/acompanhamento/{str(pedido.id)}/"
            
            # Retorna o JSON estruturado para o Frontend gerar o Cupom e o QR Code
            return Response({
                "id": str(pedido.id),
                "senha": str(pedido.id)[:4].upper(),
                "total": float(pedido.total),
                "tipo": pedido.tipo,
                "status_url": status_url,
                "criado_em": pedido.created_at.strftime("%H:%M:%S"),
                "itens": [
                    {
                        "prato": item.prato.nome, 
                        "preco": float(item.preco_unitario)
                    } for item in pedido.filas.all()
                ]
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Retorna erro amigável se algo falhar no service
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
# =========================
# PRÓXIMO PEDIDO (CAIXA / FILA LÓGICA)
# =========================

class NextOrderAPIView(APIView):
    def get(self, request):
        """Lista pedidos pendentes respeitando a prioridade de festival"""
        try:
            # Ordenação prioritária: Preferencial primeiro, depois os mais antigos
            pedidos = Pedido.objects.filter(
                status=Pedido.Status.PENDENTE
            ).order_by(
                models.Case(
                    models.When(tipo=Pedido.Tipo.PREFERENCIAL, then=models.Value(0)),
                    default=models.Value(1)
                ),
                "created_at"
            )[:10]

            data = []
            for p in pedidos:
                data.append({
                    "pedido_id": str(p.id), # O JS espera 'pedido_id'
                    "tipo": p.tipo,
                    "criado_em": p.created_at.strftime("%H:%M")
                })
            
            if not data:
                return Response(status=status.HTTP_204_NO_CONTENT)
                
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @transaction.atomic
    def post(self, request):
        pedido = Pedido.objects.filter(
            status=Pedido.Status.PENDENTE
        ).order_by(
            models.Case(
                models.When(tipo=Pedido.Tipo.PREFERENCIAL, then=models.Value(0)),
                default=models.Value(1)
            ),
            "created_at"
        ).select_for_update().first()

        if not pedido:
            return Response(status=status.HTTP_204_NO_CONTENT)

        # 1. Geramos a senha a partir dos primeiros 4 dígitos do UUID (em maiúsculo)
        senha_gerada = str(pedido.id).split('-')[0][:4].upper()

        # 2. Buscamos os itens na FilaPrato
        itens_qs = FilaPrato.objects.filter(pedido=pedido).values('prato__nome').annotate(
            qtd=models.Count('id')
        )
        
        itens_formatados = [
            {"nome": item['prato__nome'], "quantidade": item['qtd']} 
            for item in itens_qs
        ]

        pedido.status = Pedido.Status.PRODUCAO
        pedido.save(update_fields=['status'])

        return Response({
            "pedido_id": str(pedido.id),
            "senha": senha_gerada,  # Enviamos a senha pronta para o JS
            "tipo": pedido.tipo,
            "itens": itens_formatados,
            "total_itens": sum(item['qtd'] for item in itens_qs),
            "hora_impressao": timezone.now().strftime("%H:%M")
        }, status=status.HTTP_200_OK)
    
# =========================
# PAINEL DA COZINHA POR PRATO
# =========================

# core/views.py
class PainelCozinhaPratoView(APIView):
    def get(self, request, prato_id=None):
        try:
            # A MUDANÇA: Filtramos FilaPrato onde o PEDIDO está em PRODUCAO
            # E o item em si ainda está PENDENTE na cozinha.
            queryset = FilaPrato.objects.filter(
                pedido__status=Pedido.Status.PRODUCAO, # Liberado pelo atendimento
                status=FilaPrato.Status.PENDENTE       # Ainda não feito pela cozinha
            ).select_related('pedido', 'prato').order_by(
                models.Case(
                    models.When(pedido__tipo='PREFERENCIAL', then=models.Value(0)),
                    default=models.Value(1)
                ),
                'created_at'
            )

            if prato_id:
                queryset = queryset.filter(prato_id=prato_id)

            data = []
            agora = timezone.now()
            for fp in queryset:
                data.append({
                    "fila_id": str(fp.id),
                    "pedido_id": str(fp.pedido.id),
                    "prato_nome": fp.prato.nome,
                    "tipo": fp.pedido.tipo,
                    "tempo_espera": int((agora - fp.created_at).total_seconds() / 60)
                })
            
            return Response({"pendentes": data}, status=200)
        except Exception as e:
            return Response({"pendentes": [], "error": str(e)}, status=500)
# =========================
# FINALIZAR ITEM DE PRODUÇÃO
# =========================

class FinalizarPratoView(APIView):
    def post(self, request, id): # O nome aqui deve bater com o <uuid:fila_id> do urls.py
        try:
            fila = finalize_prato(id) 
            
            if not fila:
                # Se o item não for achado ou já estiver finalizado
                return Response(
                    {"detail": "Item não encontrado ou já processado."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                "status": "Finalizado", 
                "fila_id": str(id)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Retorna o erro real para o log do Django ajudar no debug
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
# AUXILIAR: Listagem de Pratos para o Terminal de Caixa
class ListPratosAPIView(APIView):
    def get(self, request):
        pratos = Prato.objects.filter(ativo=True)
        return Response([
            {"id": str(p.id), "nome": p.nome, "preco": float(p.preco)} 
            for p in pratos
        ])


# tempo médio de cada prato
class TMADashboardAPIView(APIView):
    def get(self, request):
        pratos = Prato.objects.filter(ativo=True)
        data = []

        for prato in pratos:
            # Pega o TMA mais recente deste prato
            ultima_metrica = TMA.objects.filter(prato=prato).order_by('-calculado_em').first()
            
            # Se não houver TMA (menos de 10 vendas), usa o tempo padrão do cadastro
            tempo_valor = ultima_metrica.valor_tma_seg if ultima_metrica else prato.tempo_preparo_seg
            
            data.append({
                "prato_nome": prato.nome,
                "tma_minutos": round(tempo_valor / 60, 1),
                "tem_metrica": ultima_metrica is not None
            })

        return Response(data, status=200)

# acompanhar pedido   
class AcompanhamentoPedidoView(View):
    def get(self, request, pedido_id):
        # Busca o pedido ou retorna 404
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        # Passamos o pedido para o template
        return render(request, 'acompanhamento.html', {'pedido': pedido})

# Painel central
class DashboardView(View):
    def get(self, request):
        hoje = timezone.now().date()
        
        # Total geral para cálculos de ranking
        total_geral = FilaPrato.objects.filter(created_at__date=hoje).count()

        # MÉTRICA POR PRATO: 
        # Buscamos todos os pratos e trazemos as contagens e médias específicas
        metricas_pratos = Prato.objects.annotate(
            # 1. Quantidade vendida hoje
            vendidos_hoje=Count('filaprato', filter=Q(filaprato__created_at__date=hoje)),
            
            # 2. Quantidade AGUARDANDO (Status PENDENTE)
            aguardando=Count('filaprato', filter=Q(filaprato__status='PENDENTE')),
            
            # 3. Tempo Médio de Produção (TMA) específico deste prato
            tma_especifico=Avg(
                ExpressionWrapper(
                    F('filaprato__updated_at') - F('filaprato__created_at'),
                    output_field=fields.DurationField()
                ),
                filter=Q(filaprato__status='FINALIZADO', filaprato__updated_at__date=hoje)
            )
        ).order_by('-vendidos_hoje')

        # Tratamento do TMA para minutos (Python side)
        for p in metricas_pratos:
            if p.tma_especifico:
                p.tma_minutos = round(p.tma_especifico.total_seconds() / 60, 1)
            else:
                p.tma_minutos = 0

        return render(request, 'dashboard.html', {
            'metricas_pratos': metricas_pratos,
            'total_geral': total_geral,
        })

class MonitorPedidosView(TemplateView):
    template_name = "monitor_cliente.html"

class MonitorPedidosAPIView(APIView):
    def get(self, request):
        try:
            # Se o erro for 'updated_at', volte para 'created_at' temporariamente
            pedidos = Pedido.objects.filter(
                status__in=[Pedido.Status.PENDENTE, Pedido.Status.PRODUCAO, Pedido.Status.FINALIZADO]
            ).order_by('-created_at') # Teste com created_at primeiro

            data = {"pendentes": [], "preparando": [], "prontos": []}

            for p in pedidos:
                # O split de UUID pode falhar se o ID for nulo ou formato estranho
                senha = str(p.id).split('-')[0][:4].upper() if p.id else "0000"
                item = {"senha": senha, "tipo": p.tipo}
                
                if p.status == Pedido.Status.PENDENTE:
                    data["pendentes"].append(item)
                elif p.status == Pedido.Status.PRODUCAO:
                    data["preparando"].append(item)
                elif p.status == Pedido.Status.FINALIZADO:
                    data["prontos"].append(item)

            return Response(data)
        except Exception as e:
            # Isso vai imprimir o erro exato no terminal do Django
            print(f"ERRO CRÍTICO NA API: {e}")
            return Response({"error": str(e)}, status=500)