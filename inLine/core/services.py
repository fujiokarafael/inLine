from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from uuid import UUID


from .models import Pedido, FilaPrato, TMA, Prato


# =========================
# CAIXA
# =========================

def create_order(tipo, itens):
    """
    Cria um pedido com os itens fornecidos.

    itens = [
      {"prato_id": "<UUID string>", "quantidade": 3},
      {"prato_id": "<UUID string>", "quantidade": 1},
    ]
    """
    if not itens:
        raise ValueError("É necessário informar ao menos um item")

    with transaction.atomic():
        total = Decimal("0.00")

        # Criar pedido vazio inicialmente
        pedido = Pedido.objects.create(
            tipo=tipo,
            status=Pedido.Status.PENDENTE,
            total=Decimal("0.00"),
        )

        # Converter IDs para UUIDs e buscar pratos ativos
        try:
            prato_ids = [UUID(i["prato_id"]) for i in itens]
        except ValueError as e:
            raise ValueError(f"UUID inválido em itens: {e}")

        pratos = {p.id: p for p in Prato.objects.filter(id__in=prato_ids, ativo=True)}

        filas = []

        for item in itens:
            try:
                prato_id = UUID(item["prato_id"])
            except ValueError:
                raise ValueError(f"UUID inválido: {item['prato_id']}")

            prato = pratos.get(prato_id)
            if not prato:
                raise ValueError(f"Prato {prato_id} não encontrado ou inativo")

            quantidade = int(item.get("quantidade", 0))
            if quantidade <= 0:
                raise ValueError(f"Quantidade inválida para o prato {prato_id}")

            preco = prato.preco

            # Criar filas para cada unidade
            for _ in range(quantidade):
                filas.append(
                    FilaPrato(
                        pedido=pedido,
                        prato=prato,
                        preco_unitario=preco,
                        status=FilaPrato.Status.PENDENTE
                    )
                )

            total += preco * quantidade

        # Criar todas as filas de uma vez
        FilaPrato.objects.bulk_create(filas)

        # Atualizar total do pedido
        pedido.total = total
        pedido.save(update_fields=["total"])

        return pedido


# =========================
# FILA POR PRATO (COZINHA)
# =========================

def get_next_in_queue(prato_id):
    with transaction.atomic():

        for tipo in (Pedido.Tipo.PREFERENCIAL, Pedido.Tipo.NORMAL):

            candidato = (
                FilaPrato.objects
                .select_related("pedido")
                .filter(
                    prato_id=prato_id,
                    status=FilaPrato.Status.PENDENTE,
                    pedido__tipo=tipo,
                )
                .order_by("created_at")
                .first()
            )

            if not candidato:
                continue

            venceu = (
                FilaPrato.objects
                .filter(id=candidato.id, status=FilaPrato.Status.PENDENTE)
                .update(
                    status=FilaPrato.Status.EM_PRODUCAO,
                    started_at=timezone.now(),
                )
            )

            if venceu:
                return FilaPrato.objects.select_related("pedido", "prato").get(id=candidato.id)

        return None


# =========================
# FINALIZAÇÃO DE PRATO
# =========================

def finalizar_prato_by_id(fila_prato_id):
    with transaction.atomic():

        atualizado = (
            FilaPrato.objects
            .filter(id=fila_prato_id, status=FilaPrato.Status.EM_PRODUCAO)
            .update(
                status=FilaPrato.Status.RETIRADO,
                finished_at=timezone.now(),
            )
        )

        if not atualizado:
            return None

        prato = FilaPrato.objects.select_related("pedido", "prato").get(id=fila_prato_id)

        calculate_tma()

        return prato


# =========================
# MÉTRICA TMA (janela fixa)
# =========================

def calculate_tma():
    with transaction.atomic():

        pratos = (
            FilaPrato.objects
            .select_for_update()
            .filter(
                status=FilaPrato.Status.RETIRADO,
                usado_em_metrica=False,
            )
            .order_by("finished_at")[:10]
        )

        if len(pratos) < 10:
            return None

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

        return media


# =========================
# PAINEL POR PRATO
# =========================

def get_painel_prato(prato_id, limite=50):
    em_producao = (
        FilaPrato.objects
        .select_related("pedido")
        .filter(
            prato_id=prato_id,
            status=FilaPrato.Status.EM_PRODUCAO,
        )
        .order_by("started_at")[:limite]
    )

    pendentes = (
        FilaPrato.objects
        .select_related("pedido")
        .filter(
            prato_id=prato_id,
            status=FilaPrato.Status.PENDENTE,
        )
        .order_by("created_at")[:limite]
    )

    return {
        "em_producao": list(em_producao),
        "pendentes": list(pendentes),
    }
