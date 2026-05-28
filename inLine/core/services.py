import random
import uuid
from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Pedido, FilaPrato, TMA, Prato
from django.db.models import F

# =========================
# CAIXA
# =========================

def gerar_senha_aleatoria():
    # 1. Busca todas as senhas de pedidos que ainda estão rolando no restaurante
    senhas_ativas = Pedido.objects.exclude(
        status__in=[Pedido.Status.RETIRADO, Pedido.Status.CANCELADO]
    ).values_list('senha_numero', flat=True)
    
    # 2. Sorteia um número de 4 dígitos (entre 1000 e 9999). 
    # Se bater com a senha de alguém que ainda está esperando, sorteia outro.
    while True:
        senha = random.randint(1000, 9999)
        if senha not in senhas_ativas:
            return senha

@transaction.atomic
def create_order(tipo, itens, caixa=None):
    """
    Cria um pedido associado a um caixa específico, deduz os itens do estoque
    e define os status iniciais do fluxo.
    """
    # Chama a sua função existente de senha aleatória segura
    nova_senha = gerar_senha_aleatoria()
    
    # GATILHO: O Pedido agora já nasce como PRODUCAO e recebe o caixa logado
    pedido = Pedido.objects.create(
        tipo=tipo, 
        total=0,
        status=Pedido.Status.PENDENTE,  # <--- Alterado de PENDENTE para PRODUCAO
        senha_numero=nova_senha,
        caixa=caixa                     # <--- Novo campo que identifica o operador
    )
    
    total_acumulado = 0

    for item in itens:
        prato_id = item["prato_id"]
        qtd = int(item["quantidade"])

        prato = Prato.objects.select_for_update().get(id=prato_id)
        if prato.estoque < qtd:
            raise ValueError(f"Estoque insuficiente para {prato.nome}")

        Prato.objects.filter(id=prato_id).update(estoque=F('estoque') - qtd)
        prato.refresh_from_db()
        total_acumulado += (prato.preco * qtd)

        for _ in range(qtd):
            # Os itens da fila mantêm-se como PENDENTE aguardando a cozinha puxar
            FilaPrato.objects.create(
                pedido=pedido,
                prato=prato,
                preco_unitario=prato.preco,
                status=FilaPrato.Status.PENDENTE
            )

    pedido.total = total_acumulado
    pedido.save(update_fields=['total'])
    
    return pedido

def iniciar_producao_item(fila_id):
    # Força UUID se necessário
    if isinstance(fila_id, str):
        fila_id = uuid.UUID(fila_id)

    item = FilaPrato.objects.select_related('pedido').get(id=fila_id)
    
    if not item.started_at:
        item.started_at = timezone.now()  
        item.status = FilaPrato.Status.EM_PRODUCAO
        item.save(update_fields=['started_at', 'status'])
        
        # 2. A MÁGICA AQUI: Se o pedido pai ainda está PENDENTE, 
        # o clique do cozinheiro muda ele para PRODUCAO automaticamente.
        if item.pedido.status == Pedido.Status.PENDENTE:
            item.pedido.status = Pedido.Status.PRODUCAO
            item.pedido.save(update_fields=['status'])
            
    return item

# =========================
# INICIAR PRATO
# =========================

def iniciar_producao_item(fila_id):
    # Força a conversão de string para UUID caso necessário para o banco
    if isinstance(fila_id, str):
        fila_id = uuid.UUID(fila_id)

    item = FilaPrato.objects.get(id=fila_id)
    # Validação segura por string (ignora se o started_at já existir por algum bug do banco)
    if str(item.status) == 'PENDENTE':
        item.started_at = timezone.now()  
        item.status = 'EM_PRODUCAO'
        item.save(update_fields=['started_at', 'status'])
        
    # ATUALIZAÇÃO DO PAI: Se o pedido ainda está PENDENTE, vira PRODUCAO
    if str(item.pedido.status) == 'PENDENTE':
        item.pedido.status = 'PRODUCAO'
        item.pedido.save(update_fields=['status'])
    return item

# =========================
# FINALIZAÇÃO DE PRATO
# =========================



def finalize_prato(fila_id):
    try:
        with transaction.atomic():
            # 1. Busca o item com lock para evitar concorrência
            item = FilaPrato.objects.select_for_update().filter(id=fila_id).first()

            if not item or item.status == FilaPrato.Status.FINALIZADO:
                return None

            agora = timezone.now()

            # 2. GRAVAÇÃO DOS TEMPOS (O CORAÇÃO DO TMA)
            # Se o item não tiver hora de início (pulou a etapa 'em produção'), 
            # assumimos que começou agora para não quebrar o cálculo.
            if not item.started_at:
                item.started_at = item.created_at

            item.finished_at = agora  # Define o fim da produção AGORA
            item.status = FilaPrato.Status.FINALIZADO
            
            # 3. SALVAMENTO EXPLÍCITO
            # Adicionamos os campos de tempo no update_fields
            item.save(update_fields=['status', 'finished_at', 'started_at', 'updated_at'])

            # 4. Atualização do Pedido (se todos os itens do pedido acabaram)
            pedido = item.pedido
            itens_abertos = FilaPrato.objects.filter(pedido=pedido).exclude(
                status__in=[FilaPrato.Status.FINALIZADO, FilaPrato.Status.RETIRADO]
            ).exists()

            if not itens_abertos:
                pedido.status = Pedido.Status.FINALIZADO
                pedido.save(update_fields=['status'])
            
            return item
    except Exception as e:
        print(f"Erro no service finalize_prato: {e}")
        raise e


# =========================
# MÉTRICA TMA (janela fixa)
# =========================

def calculate_tma_per_prato():
    """
    Calcula o TMA focado na performance recente (Janela de até 10 unidades).
    Se houver < 10, calcula com o que houver. Se > 10, pega o lote mais recente.
    """
    # 1. Identifica pratos que possuem itens finalizados aguardando cálculo
    pratos_pendentes = FilaPrato.objects.filter(
        status=FilaPrato.Status.FINALIZADO, 
        usado_em_metrica=False,
        started_at__isnull=False,
        finished_at__isnull=False
    ).values('prato').annotate(total=models.Count('id'))

    for p in pratos_pendentes:
        prato_id = p['prato']
        try:
            with transaction.atomic():
                # 2. Busca o lote (até 10 itens) - selecionamos para update para evitar concorrência
                itens = list(
                    FilaPrato.objects.filter(
                        prato_id=prato_id,
                        status=FilaPrato.Status.FINALIZADO,
                        usado_em_metrica=False
                    )
                    .select_for_update()
                    .order_by('finished_at')[:10]
                )

                qtd = len(itens)
                if qtd == 0:
                    continue

                # 3. Cálculo da média do lote atual
                # Soma a diferença de tempo de cada item individualmente (preparo real)
                soma_segundos = sum([
                    max(0.0, (i.finished_at - i.started_at).total_seconds()) 
                    for i in itens
                ])
                
                media = soma_segundos / qtd

                # 4. Grava a nova métrica na tabela TMA
                TMA.objects.create(
                    prato_id=prato_id,
                    valor_tma_seg=media,
                    ultimo_prato_id=itens[-1].id # Referência para auditoria
                )

                # 5. Marca esses itens como processados
                FilaPrato.objects.filter(
                    id__in=[i.id for i in itens]
                ).update(usado_em_metrica=True)

        except Exception as e:
            print(f"Erro ao calcular TMA para prato {prato_id}: {e}")

# =========================
# RETIRADA DE PEDIDO (janela fixa)
# =========================

def registrar_retirada_total_pedido(pedido_id):
    try:
        with transaction.atomic():
            # 1. Busca o pedido e trava a linha no banco
            pedido = Pedido.objects.select_for_update().get(id=pedido_id)
            
            # 2. Conta quantos itens o pedido tem no total
            total_itens = pedido.filas.count()
            
            # 3. Conta quantos desses itens já estão FINALIZADOS
            total_finalizados = pedido.filas.filter(status=Pedido.Status.FINALIZADO).count()

            # REGRA DE OURO: Só passa se o total for igual ao finalizado
            if total_itens != total_finalizados:
                raise ValidationError(
                    f"Impossível retirar: O pedido tem {total_itens} itens, mas apenas {total_finalizados} estão prontos."
                )

            # 4. Se chegou aqui, todos estão prontos. Então damos baixa em tudo:
            pedido.filas.all().update(
                status=Pedido.Status.RETIRADO, 
                delivered_at=timezone.now()
            )
            
            # 5. Atualiza o status do Pedido pai
            pedido.status = Pedido.Status.RETIRADO
            pedido.save(update_fields=['status'])
            
            return pedido
            
    except Pedido.DoesNotExist:
        return None