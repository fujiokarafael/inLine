from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Pedido, FilaPrato, TMA, Prato
from django.db.models import Sum


def create_order(tipo, itens):
    """
    itens = [
      {"prato_id": UUID, "quantidade": 3},
      {"prato_id": UUID, "quantidade": 1},
    ]
    """
    with transaction.atomic():
        total = Decimal("0.00")

        pedido = Pedido.objects.create(
            tipo=tipo,
            status=Pedido.Status.PENDENTE,
            total=Decimal("0.00"),
        )

        pratos = {
            p.id: p
            for p in Prato.objects.filter(
                id__in=[i["prato_id"] for i in itens],
                ativo=True,
            )
        }

        filas = []

        for item in itens:
            prato = pratos[item["prato_id"]]
            quantidade = item["quantidade"]
            preco = prato.preco_atual

            for _ in range(quantidade):
                filas.append(
                    FilaPrato(
                        pedido=pedido,
                        prato=prato,
                        preco_unitario=preco,
                    )
                )

            total += preco * quantidade

        FilaPrato.objects.bulk_create(filas)

        pedido.total = total
        pedido.save(update_fields=["total"])

        return pedido

def get_next_prato(prato_id):
    with transaction.atomic():

        for tipo in (Pedido.Tipo.PREFERENCIAL, Pedido.Tipo.NORMAL):

            candidato = (
                FilaPrato.objects
                .select_related("pedido")
                .filter(
                    prato_id=prato_id,
                    status="PENDENTE",
                    pedido__tipo=tipo,
                )
                .order_by("created_at")
                .first()
            )

            if not candidato:
                continue

            venceu = (
                FilaPrato.objects
                .filter(id=candidato.id, status="PENDENTE")
                .update(
                    status="EM_PRODUCAO",
                    started_at=timezone.now(),
                )
            )

            if venceu:
                return candidato

        return None

def finalizar_prato_by_id(fila_prato_id):
    from .models import FilaPrato

    with transaction.atomic():
        atualizado = (
            FilaPrato.objects
            .filter(id=fila_prato_id, status="EM_PRODUCAO")
            .update(
                status="RETIRADO",
                finished_at=timezone.now(),
            )
        )

        if not atualizado:
            return False

        from .services import calculate_tma
        calculate_tma()

        return True
        prato.status = "RETIRADO"
        prato.finished_at = timezone.now()
        prato.save()

        calculate_tma()

def calculate_tma():
    with transaction.atomic():
        pratos = (
            FilaPrato.objects
            .select_for_update()
            .filter(
                finished_at__isnull=False,
                usado_em_metrica=False,
            )
            .order_by("finished_at")[:10]
        )

        if len(pratos) < 10:
            return

        inicio = pratos[0].started_at
        fim = pratos[-1].finished_at
        media = (fim - inicio).total_seconds() / 10

        TMA.objects.create(
            tempo_medio=media,
            inicio=inicio,
            fim=fim,
        )

        FilaPrato.objects.filter(
            id__in=[p.id for p in pratos]
        ).update(usado_em_metrica=True)

def get_painel_prato(prato_id, limite=50):
    """
    Retorna a fila da cozinha para um prato específico
    """
    pendentes_pref = (
        FilaPrato.objects
        .select_related("pedido", "prato")
        .filter(
            prato_id=prato_id,
            status="PENDENTE",
            pedido__tipo=Pedido.Tipo.PREFERENCIAL,
        )
        .order_by("created_at")
    )

    pendentes_normais = (
        FilaPrato.objects
        .select_related("pedido", "prato")
        .filter(
            prato_id=prato_id,
            status="PENDENTE",
            pedido__tipo=Pedido.Tipo.NORMAL,
        )
        .order_by("created_at")
    )

    em_producao = (
        FilaPrato.objects
        .select_related("pedido", "prato")
        .filter(
            prato_id=prato_id,
            status="EM_PRODUCAO",
        )
        .order_by("started_at")
    )

    return {
        "em_producao": list(em_producao[:limite]),
        "pendentes": list(pendentes_pref[:limite]) + list(pendentes_normais[:limite]),
    }


