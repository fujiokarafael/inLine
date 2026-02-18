
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .services import (
    create_order,
    finalize_prato,
)
from .models import Pedido, FilaPrato, Prato

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
        tipo = request.data.get("tipo")
        itens = request.data.get("itens", []) # Formato: [{"prato_id": "uuid", "quantidade": 1}]
        
        try:
            pedido = create_order(tipo=tipo, itens=itens)
            return Response({
                "id": str(pedido.id),
                "total": str(pedido.total),
                "status": pedido.status
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
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
        """Algoritmo de captura de SENHA (Painel Central)"""
        # Seleciona com Lock (select_for_update) para evitar chamadas duplas
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

        pedido.status = Pedido.Status.PRODUCAO
        pedido.save(update_fields=['status'])

        return Response({
            "pedido_id": str(pedido.id),
            "senha": str(pedido.id).upper()[:4],
            "tipo": pedido.tipo
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