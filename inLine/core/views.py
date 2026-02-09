from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .services import (
    create_order,
    get_next_in_queue,
    get_painel_prato,
    finalizar_prato_by_id,
)

from .models import Pedido, FilaPrato, Prato

class CreatePratoAPIView(APIView):
    def post(self, request):
        nome = request.data.get("nome")
        preco = request.data.get("preco")
        tempo = request.data.get("tempo_preparo_seg")

        if not nome or not preco or not tempo:
            return Response(
                {"error": "dados incompletos"},
                status=400
            )

        prato = Prato.objects.create(
            nome=nome,
            preco=preco,
            tempo_preparo_seg=tempo,
            ativo=True
        )

        return Response(
            {
                "id": str(prato.id),
                "nome": prato.nome,
                "preco": str(prato.preco),
                "tempo_preparo_seg": prato.tempo_preparo_seg,
                "ativo": prato.ativo,
            },
            status=201
        )


# =========================
# CRIAR PEDIDO
# =========================

class CreateOrderAPIView(APIView):
    def post(self, request):
        tipo = request.data.get("tipo")
        itens = request.data.get("itens", [])

        if tipo not in Pedido.Tipo.values:
            return Response(
                {"error": "tipo inválido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido = create_order(tipo=tipo, itens=itens)

        return Response(
            {
                "id": str(pedido.id),
                "tipo": pedido.tipo,
                "status": pedido.status,
            },
            status=status.HTTP_201_CREATED
        )


# =========================
# PRÓXIMO PEDIDO (CAIXA / FILA LÓGICA)
# =========================

class NextOrderAPIView(APIView):
    def post(self, request):
        pedido = get_next_in_queue()

        if not pedido:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response({
            "id": str(pedido.id),
            "tipo": pedido.tipo,
            "status": pedido.status
        })


# =========================
# PAINEL DA COZINHA POR PRATO
# =========================

class PainelCozinhaPratoView(APIView):

    def get(self, request, prato_id):
        painel = get_painel_prato(prato_id)

        return Response({
            "em_producao": [
                {
                    "fila_id": str(fp.id),
                    "pedido": str(fp.pedido.id),
                    "tipo": fp.pedido.tipo,
                    "inicio": fp.started_at.isoformat() if fp.started_at else None,
                }
                for fp in painel["em_producao"]
            ],
            "pendentes": [
                {
                    "fila_id": str(fp.id),
                    "pedido": str(fp.pedido.id),
                    "tipo": fp.pedido.tipo,
                    "criado": fp.created_at.isoformat(),
                }
                for fp in painel["pendentes"]
            ],
        })


# =========================
# FINALIZAR ITEM DE PRODUÇÃO
# =========================

class FinalizarPratoView(APIView):

    def post(self, request, fila_prato_id):
        try:
            fila = finalizar_prato_by_id(fila_prato_id)
        except FilaPrato.DoesNotExist:
            return Response(
                {"error": "Item de fila não encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not fila:
            return Response(
                {"error": "Prato não está em produção"},
                status=status.HTTP_409_CONFLICT
            )

        return Response({
            "fila_id": str(fila.id),
            "status": fila.status,
            "finished_at": fila.finished_at.isoformat() if fila.finished_at else None,
        }, status=status.HTTP_200_OK)


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