
import uuid
from django.db.models import Count, Avg, F, ExpressionWrapper, fields, Q
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError
from django.views import View
from django.views.generic import TemplateView
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from decimal import Decimal
from django.db.models import F, Count, Q
from django.views.generic import ListView
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated

from .services import (
    create_order,
    finalize_prato,
    calculate_tma_per_prato,
    iniciar_producao_item,
    registrar_retirada_total_pedido,
)
from .models import Pedido, FilaPrato, Prato, TMA
# =========================
# CRIAR PRATO
# =========================

class CreatePratoAPIView(APIView):
    def post(self, request):
        nome = request.data.get("nome")
        preco = request.data.get("preco")
        estoque = request.data.get("estoque")

        if not nome or not preco:
            return Response({"error": "Nome e preço são obrigatórios"}, status=400)

        try:
            prato = Prato.objects.create(
                nome=nome,
                preco=preco,
                estoque=estoque,
                ativo=True
            )
            return Response({"id": str(prato.id), "status": "salvo"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# =========================
# CRIAR PEDIDO
# =========================

# views.py
class CreateOrderAPIView(APIView):
    # ADICIONE ESTAS DUAS LINHAS PARA RESOLVER O ERRO 403:
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        tipo = request.data.get("tipo")
        itens = request.data.get("itens", [])
        
        # A API recebe o texto que o JavaScript enviou (o número do terminal)
        terminal_caixa = request.data.get("caixa", "Não Identificado")
        
        try:
            # Envia o texto para o service
            pedido = create_order(tipo=tipo, itens=itens, caixa=terminal_caixa)
            
            host = request.get_host() 
            status_url = f"http://{host}/acompanhamento/{str(pedido.id)}/"
            
            return Response({
                "id": str(pedido.id),
                "senha": str(pedido.senha_numero),
                "tipo": pedido.tipo,
                "total": float(pedido.total),
                "status_url": status_url
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": "Erro interno ao processar pedido."}, status=500)       
# =========================
# LISTA DE PEDIDOS (CAIXA / FILA LÓGICA)
# =========================

# views.py
class AtendimentoListaAPIView(APIView):
    def get(self, request, pedido_id=None):
        hoje = timezone.now().date()
        
        queryset = Pedido.objects.filter(
            created_at__date=hoje
        ).prefetch_related('filas__prato').order_by(
            models.Case(
                models.When(tipo='PREFERENCIAL', then=models.Value(0)),
                default=models.Value(1)
            ),
            '-created_at' 
        )

        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(id__icontains=search)

        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        data = []
        for p in queryset:
            itens_agrupados = p.filas.values(
                'prato__nome', 'preco_unitario'
            ).annotate(quantidade=Count('id'))

            data.append({
                "id": str(p.id),
                "senha": str(p.senha_numero),
                "tipo": p.tipo,
                "status": p.status,
                "caixa": p.caixa,
                "total": float(p.total),
                "criado_em": timezone.localtime(p.created_at).strftime("%H:%M"),
                "itens": [
                    {
                        "nome": item['prato__nome'],
                        "qtd": item['quantidade'],
                        "preco": float(item['preco_unitario']),
                        "subtotal": float(item['preco_unitario'] * item['quantidade'])
                    } for item in itens_agrupados
                ]
            })
        return Response(data)

    @transaction.atomic
    def post(self, request, pedido_id):
        # O Atendimento não envia mais para produção! Serve apenas para cancelamento manual.
        acao = request.data.get("acao")
        pedido = get_object_or_404(Pedido.objects.select_for_update(), id=pedido_id)

        if acao == "CANCELAR":
            pedido.status = Pedido.Status.CANCELADO
            pedido.save(update_fields=['status'])
            pedido.filas.all().update(status=FilaPrato.Status.CANCELADO)
            return Response({"status": "sucesso", "msg": "Pedido cancelado com sucesso."})

        return Response({"error": "Ação inválida para este fluxo"}, status=400)
# =========================
# PAINEL DA COZINHA POR PRATO
# =========================

# core/views.py
class PainelCozinhaPratoView(APIView):
    def get(self, request, prato_id=None):
        try:
            # AJUSTE: Permite ver pedidos PENDENTES e em PRODUCAO
            queryset = FilaPrato.objects.filter(
                pedido__status__in=[Pedido.Status.PENDENTE, Pedido.Status.PRODUCAO], 
                status__in=[FilaPrato.Status.PENDENTE, FilaPrato.Status.EM_PRODUCAO]
            ).select_related('pedido', 'prato').order_by(
                models.Case(
                    models.When(pedido__tipo='PREFERENCIAL', then=models.Value(0)),
                    default=models.Value(1)
                ),
                'created_at'
            )

            if prato_id:
                queryset = queryset.filter(prato_id=prato_id)

            data = []
            agora = timezone.now()
            for fp in queryset:
                data.append({
                    "fila_id": str(fp.id),
                    "pedido_id": str(fp.pedido.id),
                    "senha": str(fp.pedido.senha_numero),
                    "prato_nome": fp.prato.nome,
                    "tipo": fp.pedido.tipo,
                    "status_item": fp.status, # PENDENTE ou EM_PRODUCAO
                    "tempo_espera": int((agora - fp.created_at).total_seconds() / 60)
                })
            
            return Response({"pendentes": data}, status=200)
        except Exception as e:
            return Response({"pendentes": [], "error": str(e)}, status=500)

# =========================
# AÇÃO 1: COLOCAR EM PRODUÇÃO
# =========================
class IniciarPratoView(APIView):
    def post(self, request, id):
        try:
            fila = iniciar_producao_item(id)
            return Response({
                "status": "EM_PRODUCAO",
                "fila_id": str(id),
                "mensagem": "Item entrou em preparação."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"--- ERRO CRÍTICO NO INICIAR_PRATO: {e} ---")
            return Response({"error": str(e)}, status=500)


# =========================
# FINALIZAR ITEM DE PRODUÇÃO
# =========================

class FinalizarPratoView(APIView):
    def post(self, request, id): 
        try:
            fila = finalize_prato(id) 
            
            if not fila:
                return Response(
                    {"detail": "Item não encontrado ou já processado."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            try:
                calculate_tma_per_prato()
            except Exception as tma_err:
                print(f"Aviso: Falha ao calcular TMA: {tma_err}")

            return Response({
                "status": "FINALIZADO", 
                "fila_id": str(id),
                "mensagem": "Item finalizado e métricas processadas."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    
# AUXILIAR: Listagem de Pratos para o Terminal de Caixa

class ListPratosAPIView(APIView):
    def get(self, request):
        # Não precisa mais de 'hoje', 'Count' ou 'annotate'
        # Apenas pegue o valor real que está na coluna 'estoque'
        pratos = Prato.objects.filter(ativo=True)
        
        return Response([
            {
                "id": str(p.id), 
                "nome": p.nome, 
                "preco": float(p.preco), 
                "estoque": p.estoque # <--- Use o campo puro do banco
            } 
            for p in pratos
        ])

# tempo médio de cada prato
class TMADashboardAPIView(APIView):
    def get(self, request):
        pratos = Prato.objects.filter(ativo=True)
        data = []

        for prato in pratos:
            # Pega a métrica mais recente calculada pelo service
            ultima_metrica = TMA.objects.filter(prato=prato).order_by('-calculado_em').first()
            
            # Cálculo seguro: se não houver métrica, tma_minutos é 0
            if ultima_metrica and ultima_metrica.valor_tma_seg:
                tma_minutos = round(float(ultima_metrica.valor_tma_seg) / 60, 1)
            else:
                tma_minutos = 0.0

            data.append({
                "prato_nome": prato.nome,
                "tma_minutos": tma_minutos,
                "tem_metrica": ultima_metrica is not None
            })

        return Response(data, status=200)
    
# acompanhar pedido   
class AcompanhamentoPedidoView(View):
    def get(self, request, pedido_id):
        # Busca o pedido ou retorna 404
        pedido = get_object_or_404(Pedido, id=pedido_id)
        
        # Passamos o pedido para o template
        return render(request, 'acompanhamento.html', {'pedido': pedido})

# Painel central
class DashboardView(View):
    def get(self, request):
        hoje = timezone.now().date()
        total_geral = FilaPrato.objects.filter(created_at__date=hoje).count()

        # Busca pratos e anota as contagens básicas
        metricas_pratos = Prato.objects.annotate(
            vendidos_hoje=Count('filas', filter=Q(filas__created_at__date=hoje)),
            aguardando=Count('filas', filter=Q(filas__status='PENDENTE', filas__pedido__status='PENDENTE')),
            estoque_atual= F('estoque')
        ).order_by('-vendidos_hoje')

        for p in metricas_pratos:
            # TENTA BUSCAR NA TABELA TMA (Métrica processada)
            ultima_m = TMA.objects.filter(prato_id=p.id).order_by('-calculado_em').first()
            
            if ultima_m and ultima_m.valor_tma_seg:
                p.tma_minutos = round(float(ultima_m.valor_tma_seg) / 60, 1)
            else:
                # FALLBACK: Se o banco TMA está vazio, calcula a média real dos itens de HOJE
                media_hoje = FilaPrato.objects.filter(
                    prato_id=p.id, 
                    status='FINALIZADO', 
                    finished_at__date=hoje,
                    started_at__isnull=False
                ).aggregate(
                    media=Avg(ExpressionWrapper(F('finished_at') - F('started_at'), output_field=fields.DurationField()))
                )['media']
                
                if media_hoje:
                    p.tma_minutos = round(media_hoje.total_seconds() / 60, 1)
                else:
                    p.tma_minutos = 0.0

        return render(request, 'dashboard.html', {
            'metricas_pratos': metricas_pratos, 
            'total_geral': total_geral
        })
    

class MonitorPedidosView(TemplateView):
    template_name = "monitor_cliente.html"


class MonitorPedidosAPIView(APIView):
    def get(self, request):
        try:
            # Usamos created_at se o updated_at ainda der erro de coluna não encontrada
            pedidos = Pedido.objects.filter(
                status__in=[Pedido.Status.PENDENTE, Pedido.Status.PRODUCAO, Pedido.Status.FINALIZADO]
            ).order_by('-created_at')

            data = {"pendentes": [], "preparando": [], "prontos": []}

            for p in pedidos:
                senha = str(p.senha_numero) if p.senha_numero else "0000"
                item = {"senha": senha, "tipo": p.tipo}
                
                if p.status == Pedido.Status.PENDENTE:
                    data["pendentes"].append(item)
                elif p.status == Pedido.Status.PRODUCAO:
                    data["preparando"].append(item)
                elif p.status == Pedido.Status.FINALIZADO:
                    # CORREÇÃO AQUI: 
                    # Certifique-se que o campo no modelo FilaPrato chama-se 'filas'
                    itens_agrupados = p.filas.values('prato__nome').annotate(
                        total=Count('id')
                    )
                    
                    item["itens"] = [
                        {
                            "nome": i['prato__nome'],
                            "quantidade": i['total']
                        } for i in itens_agrupados
                    ]
                    data["prontos"].append(item)

            return Response(data)
        except Exception as e:
            # ESSA LINHA É A MAIS IMPORTANTE AGORA:
            # Verifique o log do seu terminal para ler o que aparecer aqui!
            print(f"--- ERRO NA API DO MONITOR: {e} ---")
            return Response({"error": str(e)}, status=500)

#ALTERAR STATUS PARA RETIRADO DO PEDIDO
class RetirarPedidoView(APIView):
    def post(self, request, pedido_id):
        try:
            pedido = registrar_retirada_total_pedido(pedido_id)
            
            if not pedido:
                return Response({"detail": "Pedido não encontrado."}, status=404)

            return Response({"status": "sucesso"}, status=200)

        except ValidationError as e:
            # Retorna 400 (Bad Request) com a mensagem explicativa
            return Response({"detail": list(e.messages)}, status=400)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

#DAR BAIXA DO PEDIDO FINALIZADO DO SISTEMA

class BaixaEntregaView(View):
    def get(self, request):
        # 1. Pegamos os pedidos que não foram retirados ainda
        # 2. Contamos o total de itens (total_itens)
        # 3. Contamos apenas os itens que estão FINALIZADOS (total_prontos)
        pedidos_completos = Pedido.objects.annotate(
            total_itens=Count('filas'),
            total_prontos=Count('filas', filter=Q(filas__status=Pedido.Status.FINALIZADO))
        ).filter(
            status=Pedido.Status.FINALIZADO, # O status do pedido pai
            total_itens=models.F('total_prontos'), # Regra: Total == Prontos
            total_itens__gt=0 # Garante que não pegamos pedidos vazios
        ).prefetch_related('filas', 'filas__prato').order_by('created_at')

        return render(request, 'baixa_entrega.html', {
            'pedidos_prontos': pedidos_completos
        })

#Atualizar prato
class UpdatePratoAPIView(APIView):
    def put(self, request, prato_id):
        try:
            # 1. Busca o prato
            try:
                prato = Prato.objects.get(id=prato_id)
            except (Prato.DoesNotExist, ValueError):
                return Response({"error": "Prato não encontrado ou ID inválido."}, status=status.HTTP_404_NOT_FOUND)

            # 2. Captura dados
            nome = request.data.get("nome")
            preco = request.data.get("preco")
            estoque = request.data.get("estoque")
            ativo = request.data.get("ativo")

            # 3. Atualização Segura
            if nome:
                prato.nome = nome
            
            if preco is not None and str(preco).strip() != "":
                try:
                    # Converte para string, troca vírgula por ponto e vira Decimal
                    valor_limpo = str(preco).replace(',', '.').strip()
                    prato.preco = Decimal(valor_limpo)
                except Exception:
                    return Response({"error": "Formato de preço inválido."}, status=400)
            
            if estoque is not None and str(estoque).strip() != "":
                prato.estoque = int(estoque)
                
            if ativo is not None:
                prato.ativo = str(ativo).lower() in ['true', '1', 't', 'y', 'yes']

            # 4. Salva e retorna
            prato.save()

            return Response({
                "id": str(prato.id),
                "status": "atualizado",
                "nome": prato.nome,
                "preco": str(prato.preco),
                "estoque_atual": prato.estoque
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Verifique seu terminal, o erro real aparecerá aqui:
            print(f"--- ERRO NO UPDATE: {e} ---") 
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# PAINEL DE PRODUÇÃO QUANTITATIVO

class PainelQuantitativoProducaoAPIView(APIView):
    def get(self, request):
        try:
            # Usamos FilaPrato como base, mas agrupamos pelo Prato
            dados = FilaPrato.objects.filter(
                pedido__status__in=[Pedido.Status.PENDENTE, Pedido.Status.PRODUCAO]
            ).values('prato__nome', 'prato__estoque').annotate(
                # Conta apenas os PENDENTES (Espera)
                espera=Count('id', filter=Q(status=FilaPrato.Status.PENDENTE)),
                # Conta apenas os EM_PRODUCAO (Chapa)
                producao=Count('id', filter=Q(status=FilaPrato.Status.EM_PRODUCAO))
            ).order_by('-producao', '-espera')

            return Response(dados, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# PAINEL DE PRODUÇÃO POR PRODUTO

class PainelPorPratoView(TemplateView):
    template_name = 'painel_prato.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prato_id_str = self.kwargs.get('id')
        
        try:
            # 1. Converte a string contínua da URL para o formato UUID do banco
            prato_uuid = uuid.UUID(str(prato_id_str))
            prato = Prato.objects.filter(id=prato_uuid).first()
            
            # 2. Conta apenas os itens que estão na chapa (Status EM_PRODUCAO)
            qtd_producao = FilaPrato.objects.filter(
                prato_id=prato_uuid,
                status=FilaPrato.Status.EM_PRODUCAO
            ).count()

            # 3. Conta apenas os itens em espera (Status PENDENTE)
            # Adicionamos o filtro no pedido pai para garantir que só contamos itens de pedidos ativos
            qtd_pendente = FilaPrato.objects.filter(
                prato_id=prato_uuid,
                status=FilaPrato.Status.PENDENTE,
                pedido__status__in=[Pedido.Status.PENDENTE, Pedido.Status.PRODUCAO]
            ).count()

            # 4. Alimenta as variáveis que o HTML está esperando
            context['prato_id'] = str(prato_uuid)
            context['nome_prato'] = prato.nome if prato else "Prato não encontrado"
            context['qtd_producao'] = qtd_producao
            context['qtd_pendente'] = qtd_pendente
            context['qtd_estoque'] = prato.estoque if prato else 0
            
        except (ValueError, TypeError):
            # Fallback de segurança para URLs corrompidas
            context['prato_id'] = None
            context['nome_prato'] = "Prato/ID Inválido"
            context['qtd_producao'] = 0
            context['qtd_pendente'] = 0
            context['qtd_estoque'] = 0
            
        return context

# MONITOR DE ULTIMA SENHA CHAMADA
class ExpedicaoPedidosAPIView(APIView):
    def get(self, request):
        try:
            # Filtra pedidos finalizados nos últimos 5 minutos
            cinco_minutos_atras = timezone.now() - timedelta(minutes=5)
            
            pedidos_prontos = Pedido.objects.filter(
                status=Pedido.Status.FINALIZADO,
                updated_at__gte=cinco_minutos_atras  # <--- ESSA É A CHAVE
            ).order_by('-updated_at') # Ordena pelo mais recente
            
            data = {"prontos": []}
            
            for p in pedidos_prontos:
                # ... (resto do seu loop permanece igual)
                data["prontos"].append({
                    "id": str(p.id),
                    "senha": str(p.senha_numero),
                    # ...
                })
                
            return Response(data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
class ExpedicaoPainelView(TemplateView):
    template_name = 'expedicao.html'
    
    # Opcional: Adicione contextos iniciais se precisar
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Painel de Expedição"
        return context