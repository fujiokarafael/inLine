from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import get_painel_prato, finalizar_prato_by_id

from .services import create_order, get_next_in_queue
from .models import Pedido

class CreateOrderAPIView(APIView):
    def post(self, request):
        tipo = request.data.get("tipo")
        pedido = create_order(tipo)
        return Response(
            {"id": str(pedido.id), "tipo": pedido.tipo},
            status=status.HTTP_201_CREATED
        )


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

class PainelCozinhaPratoView(APIView):

    def get(self, request, prato_id):
        painel = get_painel_prato(prato_id)

        return Response({
            "em_producao": [
                {
                    "fila_id": str(fp.id),
                    "pedido": str(fp.pedido.id),
                    "tipo": fp.pedido.tipo,
                    "inicio": fp.started_at,
                }
                for fp in painel["em_producao"]
            ],
            "pendentes": [
                {
                    "fila_id": str(fp.id),
                    "pedido": str(fp.pedido.id),
                    "tipo": fp.pedido.tipo,
                    "criado": fp.created_at,
                }
                for fp in painel["pendentes"]
            ],
        })

class FinalizarPratoView(APIView):
    def post(self, request, fila_prato_id):
        ok = finalizar_prato_by_id(fila_prato_id)

        if not ok:
            return Response({"erro": "Prato não está em produção"}, status=409)

        return Response({"status": "finalizado"})
