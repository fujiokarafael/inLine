from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .services import (
    create_order,
    get_next_in_queue,
    get_painel_prato,
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
        """ Retorna a lista de pedidos aguardando chamada """
        try:
            pedidos_pendentes = Pedido.objects.filter(
                status=Pedido.Status.PENDENTE
            ).order_by('-tipo', 'created_at')

            data = []
            for pedido in pedidos_pendentes:
                # Buscamos manualmente o primeiro item da fila para este pedido
                item = FilaPrato.objects.filter(pedido=pedido).first()
                
                data.append({
                    "id": str(pedido.id),
                    "pedido_id": str(pedido.id),
                    "tipo": pedido.tipo,
                    "prato": item.prato.nome if item and item.prato else "Diversos",
                    "criado_em": pedido.created_at.strftime("%H:%M")
                })
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Erro no Atendimento (GET): {e}")
            return Response({"error": "Falha ao listar pedidos"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """ Processa a chamada do próximo pedido """
        try:
            # Seleciona o primeiro da fila (Preferencial > Antiguidade)
            pedido = Pedido.objects.filter(
                status=Pedido.Status.PENDENTE,
            ).order_by('-tipo', 'created_at').first()

            if not pedido:
                return Response(status=status.HTTP_204_NO_CONTENT)

            # Busca o prato para exibir na senha
            item = FilaPrato.objects.filter(pedido=pedido).first()
            nome_prato = item.prato.nome if item and item.prato else "Diversos"

            # Atualiza o status para PRODUCAO (sai da fila de pendentes)
            pedido.status = Pedido.Status.PRODUCAO 
            pedido.save(update_fields=['status'])

            return Response({
                "pedido_id": str(pedido.id),
                "prato": nome_prato,
                "tipo": pedido.tipo
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Erro no Atendimento (POST): {e}")
            return Response({"error": "Erro ao processar chamada"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# =========================
# PAINEL DA COZINHA POR PRATO
# =========================

class PainelCozinhaPratoView(APIView):
    def get(self, request, prato_id=None):
        try:
            # Busca direta para garantir que os dados apareçam
            # Filtramos por PENDENTE para aparecer na cozinha
            queryset = FilaPrato.objects.filter(
                status=FilaPrato.Status.PENDENTE
            ).select_related('pedido', 'prato').order_by('pedido__created_at')

            if prato_id:
                queryset = queryset.filter(prato_id=prato_id)

            data = []
            for fp in queryset:
                data.append({
                    "fila_id": str(fp.id),
                    "pedido_id": str(fp.pedido.id),
                    "prato_nome": fp.prato.nome,
                    "tipo": fp.pedido.tipo,
                    "criado_em": fp.created_at.strftime("%H:%M"),
                    "tempo_espera": int((timezone.now() - fp.created_at).total_seconds() / 60)
                })
            
            return Response({"pendentes": data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Erro na Produção: {e}")
            return Response({"pendentes": [], "error": str(e)}, status=500)
# =========================
# FINALIZAR ITEM DE PRODUÇÃO
# =========================

class FinalizarPratoView(APIView):
    def post(self, request, fila_prato_id):
        fila = finalize_prato(fila_prato_id) 
        if not fila:
            return Response(status=status.HTTP_409_CONFLICT)

        return Response({"status": "Finalizado", "fila_id": str(fila.id)})


class PratoNextAPIView(APIView):

    """
    Retorna o próximo item pendente na fila para um prato específico.
    """

    def get(self, request, prato_id):
        try:
            prato = Prato.objects.get(id=prato_id, ativo=True)
        except Prato.DoesNotExist:
            return Response(
                {"error": "Prato não encontrado ou inativo"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Buscar o próximo item pendente na fila
        fila_pendente = (
            FilaPrato.objects
            .filter(prato=prato, status=FilaPrato.Status.PENDENTE)
            .order_by("pedido__created_at")  # ou outro critério de prioridade
            .first()
        )

        if not fila_pendente:
            return Response(
                {"error": f"Nenhum item na fila do prato {prato.nome}"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Retornar dados do item pendente
        return Response({
            "fila_id": str(fila_pendente.id),
            "pedido_id": str(fila_pendente.pedido.id),
            "prato": prato.nome,
            "tipo_pedido": fila_pendente.pedido.tipo,
            "status": fila_pendente.status,
            "criado": fila_pendente.created_at.isoformat()
        })
class IniciarPratoView(APIView):

    """
    Marca um item da fila como EM_PRODUCAO
    """

    def post(self, request, fila_prato_id):
        try:
            fila = FilaPrato.objects.get(id=fila_prato_id)
        except FilaPrato.DoesNotExist:
            return Response({"error": "Item da fila não encontrado"}, status=404)

        if fila.status != FilaPrato.Status.PENDENTE:
            return Response({"error": f"Item não pode ser iniciado, status atual: {fila.status}"}, status=400)

        fila.status = FilaPrato.Status.EM_PRODUCAO
        fila.started_at = timezone.now()
        fila.save(update_fields=["status", "started_at"])

        return Response({
            "fila_id": str(fila.id),
            "status": fila.status,
            "started_at": fila.started_at.isoformat()
        })
    
# AUXILIAR: Listagem de Pratos para o Terminal de Caixa
class ListPratosAPIView(APIView):
    def get(self, request):
        pratos = Prato.objects.filter(ativo=True)
        return Response([
            {"id": str(p.id), "nome": p.nome, "preco": float(p.preco)} 
            for p in pratos
        ])