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
# FINALIZAÇÃO DE PRATO
# =========================

def finalize_prato(fila_id):
    try:
        with transaction.atomic():
            # 1. Busca o item específico (select_for_update evita duplicidade)
            item = FilaPrato.objects.select_for_update().filter(id=fila_id).first()

            if not item or item.status == FilaPrato.Status.FINALIZADO:
                return None

            # 2. Atualiza o status do item
            item.status = FilaPrato.Status.FINALIZADO
            item.save(update_fields=['status'])
            
            # 3. VERIFICAÇÃO CRÍTICA: O Pedido Pai
            pedido = item.pedido
            
            # Buscamos se existe QUALQUER prato desse pedido que ainda esteja 
            # PENDENTE ou EM_PRODUCAO.
            # Se .exists() for False, significa que todos estão FINALIZADOS.
            tem_itens_em_aberto = FilaPrato.objects.filter(
                pedido=pedido
            ).exclude(
                status__in=[FilaPrato.Status.FINALIZADO, FilaPrato.Status.RETIRADO]
            ).exists()

            if not tem_itens_em_aberto:
                pedido.status = Pedido.Status.FINALIZADO
                pedido.save(update_fields=['status'])
                # Log de debug interno (opcional)
                print(f"DEBUG: Pedido {pedido.id} movido para FINALIZADO")
            
            return item
    except Exception as e:
        print(f"ERRO NO SERVICE: {e}")
        raise e


# =========================
# MÉTRICA TMA (janela fixa)
# =========================

def calculate_tma_per_prato():
    """
    Calcula o TMA segmentado por prato (Janela de 10 unidades).
    Processa apenas itens com status RETIRADO que ainda não foram contabilizados.
    """
    # 1. Identifica quais pratos têm pelo menos 10 itens aguardando cálculo
    # Usamos um subquery ou agregação simples para performance
    pratos_ids = FilaPrato.objects.filter(
        status=FilaPrato.Status.RETIRADO,
        usado_em_metrica=False
    ).values('prato').annotate(
        total=models.Count('id')
    ).filter(total__gte=10).values_list('prato', flat=True)

    resultados = []

    for prato_id in pratos_ids:
        try:
            with transaction.atomic():
                # 2. Busca exatamente 10 e trava para escrita (select_for_update)
                # O SQLite (modo WAL) lidará com o lock por linha
                itens = list(
                    FilaPrato.objects.filter(
                        prato_id=prato_id,
                        status=FilaPrato.Status.RETIRADO,
                        usado_em_metrica=False
                    )
                    .select_for_update()
                    .order_by("finished_at")[:10]
                )

                # Validação de segurança (caso outro processo tenha pego)
                if len(itens) < 10:
                    continue

                # 3. Cálculo: Tempo entre o 10º finalizado e o 1º iniciado do lote
                t_inicial = itens[0].started_at
                t_final = itens[-1].finished_at
                
                if t_inicial and t_final:
                    diff_segundos = max(0.0, (t_final - t_inicial).total_seconds())
                    media = diff_segundos / 10

                    # 4. Persistência vinculada ao Prato específico
                    TMA.objects.create(
                        prato_id=prato_id,
                        valor_tma_seg=media,
                        ultimo_prato_id=itens[-1].id
                    )

                    # 5. Marca os 10 itens como "usados" para não repetir no próximo cálculo
                    FilaPrato.objects.filter(
                        id__in=[i.id for i in itens]
                    ).update(usado_em_metrica=True)

                    resultados.append({
                        "prato_id": prato_id, 
                        "media_seg": media
                    })

        except Exception as e:
            print(f"Erro ao calcular TMA para prato {prato_id}: {e}")
            continue

    return resultados