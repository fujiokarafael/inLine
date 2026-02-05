from django.db import transaction
from django.utils import timezone

from .models import Pedido, FilaPrato, TMA


def create_order(tipo):
    with transaction.atomic():
        return Pedido.objects.create(
            tipo=tipo,
            status=Pedido.Status.PENDENTE,
        )
def get_next_in_queue():
    for tipo in (Pedido.Tipo.PREFERENCIAL, Pedido.Tipo.NORMAL):
        with transaction.atomic():
            candidato = (
                Pedido.objects
                .filter(
                    status=Pedido.Status.PENDENTE,
                    tipo=tipo,
                )
                .order_by("created_at")
                .first()
            )

            if not candidato:
                return None

            venceu = (
                Pedido.objects
                .filter(
                    id=candidato.id,
                    status=Pedido.Status.PENDENTE,
                )
                .update(status=Pedido.Status.PRODUCAO)
            )

            if venceu:
                return candidato

    return None
def finalizar_prato(prato):
    with transaction.atomic():
        prato.finished_at = timezone.now()
        prato.save()

        calculate_tma()
def calculate_tma():
    with transaction.atomic():
        pratos = (
            FilaPrato.objects
            .select_for_update()
            .filter(finished_at__isnull=False, usado_em_metrica=False)
            .order_by("finished_at")[:10]
        )

        if len(pratos) < 10:
            return

        # calcula, persiste, marca usados
