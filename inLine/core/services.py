from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from uuid import UUID
from .models import Pedido, FilaPrato, TMA, Prato


# =========================
# CAIXA
# =========================

def create_order(tipo, itens):
    if not itens:
        raise ValueError("É necessário informar ao menos um item")

    with transaction.atomic():
        # 1. Criar pedido inicial
        pedido = Pedido.objects.create(
            tipo=tipo,
            total=Decimal("0.00"),
        )

        # 2. Preparar dados e buscar pratos de uma vez só (Otimização)
        try:
            prato_ids = [UUID(str(i["prato_id"])) for i in itens]
        except (ValueError, KeyError):
            raise ValueError("Formato de ID de prato inválido")

        # Busca todos os pratos necessários em uma única query
        pratos_db = {p.id: p for p in Prato.objects.filter(id__in=prato_ids)}
        
        filas_para_criar = []
        total_acumulado = Decimal("0.00")

        # 3. Processar itens
        for item in itens:
            p_id = UUID(str(item["prato_id"]))
            prato = pratos_db.get(p_id)
            
            if not prato:
                raise ValueError(f"Prato {p_id} não encontrado")

            quantidade = int(item.get("quantidade", 1))
            preco_no_momento = prato.preco # Assume que seu model Prato tem o campo 'preco'

            # Criar objetos FilaPrato na memória
            for _ in range(quantidade):
                filas_para_criar.append(
                    FilaPrato(
                        pedido=pedido,
                        prato=prato,
                        preco_unitario=preco_no_momento,
                        status=FilaPrato.Status.PENDENTE
                    )
                )
            
            total_acumulado += (preco_no_momento * quantidade)

        # 4. Persistir no banco em massa
        FilaPrato.objects.bulk_create(filas_para_criar)

        # 5. Atualizar o total do pedido
        pedido.total = total_acumulado
        pedido.save(update_fields=["total"])

        return pedido


# =========================
# FILA POR PRATO (COZINHA)
# =========================

def get_next_in_queue(prato_id):
    """
    Algoritmo determinístico de captura.
    Prioriza PREFERENCIAL sobre NORMAL via SQL puro para atomicidade.
    """
    with transaction.atomic():
        # 1. Busca candidata respeitando a ordem de prioridade absoluta
        # Usamos uma subquery ou ordenação composta para ser atômico
        candidato = (
            FilaPrato.objects.filter(
                prato_id=prato_id,
                status=FilaPrato.Status.PENDENTE
            )
            .order_by(
                models.Case(
                    models.When(pedido__tipo=Pedido.Tipo.PREFERENCIAL, then=models.Value(0)),
                    default=models.Value(1)
                ),
                "created_at"
            )
            .select_for_update(skip_locked=False) # SQLite não suporta SKIP LOCKED, usamos soft-lock
            .first()
        )

        if not candidato:
            return None

        # 2. Soft-lock determinístico: Só atualiza se ainda estiver PENDENTE
        agora = timezone.now()
        atualizados = FilaPrato.objects.filter(
            id=candidato.id, 
            status=FilaPrato.Status.PENDENTE
        ).update(
            status=FilaPrato.Status.EM_PRODUCAO, # Alinhado com o status do Model anterior
            started_at=agora
        )

        if atualizados > 0:
            return FilaPrato.objects.select_related("pedido", "prato").get(id=candidato.id)
        
        return None


# =========================
# FINALIZAÇÃO DE PRATO
# =========================

def finalize_prato(fila_prato_id):
    """
    Finaliza e dispara métricas atomicamente.
    """
    with transaction.atomic():
        rows = FilaPrato.objects.filter(
            id=fila_prato_id, 
            status=FilaPrato.Status.EM_PRODUCAO
        ).update(
            status=FilaPrato.Status.RETIRADO,
            finished_at=timezone.now()
        )

        if rows == 0:
            return None

        # Trigger automático de métrica após finalização
        media_atualizada = calculate_tma()
        
        return FilaPrato.objects.get(id=fila_prato_id)


# =========================
# MÉTRICA TMA (janela fixa)
# =========================

def calculate_tma():
    """
    Métricas baseadas em janela móvel fixa de 10 unidades.
    Totalmente compatível com o Model TMA (valor_tma_seg, ultimo_prato_id).
    """
    with transaction.atomic():
        # 1. Busca exatamente 10 e trava para escrita (select_for_update)
        # Nota: Usamos FilaPrato.Status.RETIRADO conforme o desafio técnico
        pratos = list(
            FilaPrato.objects.filter(
                status=FilaPrato.Status.RETIRADO,
                usado_em_metrica=False
            )
            .select_for_update()
            .order_by("finished_at")[:10]
        )

        # 2. Validação da janela de 10 unidades
        if len(pratos) < 10:
            return None

        t_inicial = pratos[0].started_at
        t_final = pratos[-1].finished_at
        
        # 3. Cálculo com segurança contra drift de relógio
        diff_segundos = max(0.0, (t_final - t_inicial).total_seconds())
        media = diff_segundos / 10

        # 4. Persistência (Nomes de campos alinhados ao seu MODEL)
        TMA.objects.create(
            valor_tma_seg=media,        # Compatível com seu Model
            ultimo_prato_id=pratos[-1].id # Auditabilidade conforme seu Model
            # calculado_em é auto_now_add, não precisa passar aqui
        )

        # 5. Atualização atômica para evitar reuso do prato em outro cálculo
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
