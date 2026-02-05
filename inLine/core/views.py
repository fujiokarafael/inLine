from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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

# Create your views here.
