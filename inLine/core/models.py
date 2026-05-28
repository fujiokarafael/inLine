import uuid
from django.db import models
from django.contrib.auth.models import User



# =========================
# PEDIDO (CAIXA)
# =========================

class Pedido(models.Model):

    class Tipo(models.TextChoices):
        NORMAL = "NORMAL"
        PREFERENCIAL = "PREFERENCIAL"

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE"
        PRODUCAO = "PRODUCAO"
        FINALIZADO = "FINALIZADO"
        RETIRADO = "RETIRADO"
        CANCELADO="CANCELADO"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    senha_numero = models.IntegerField(null=True, blank=True, db_index=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE, db_index=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True, db_index=True) # Essencial para a fila da Expedição
    caixa = models.CharField(
        max_length=50, 
        null=True, 
        blank=True, 
        help_text="Identificador digitado no terminal (Ex: Caixa 01)"
    )

    class Meta:
        indexes = [
            models.Index(fields=["status", "tipo", "created_at"]),
            models.Index(fields=["status", "updated_at"]),
        ]
    
    def __str__(self):
        return f"Pedido #{self.senha_numero} - Terminal: {self.caixa or 'Não info'}"

# =========================
# PRATO (CATÁLOGO)
# =========================

class Prato(models.Model):  
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True, db_index=True)
    estoque=models.IntegerField(default=100,null=False, blank=False)

    class Meta:
        indexes = [
            models.Index(fields=["ativo"]),
        ]


# =========================
# FILA DE PRODUÇÃO (1 UNIDADE = 1 LINHA)
# =========================

class FilaPrato(models.Model):

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE"
        EM_PRODUCAO = "EM_PRODUCAO"
        FINALIZADO = "FINALIZADO"
        RETIRADO = "RETIRADO"
        CANCELADO="CANCELADO"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="filas")
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT, null=True, related_name="filas")
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True )
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)
    usado_em_metrica = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["prato", "status", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["status", "created_at"], name="idx_fila_prioridade"),
            models.Index(fields=["created_at"]),
            models.Index(fields=["usado_em_metrica", "status", "finished_at"]),
        ]


# =========================
# MÉTRICA (TMA)
# =========================

class TMA(models.Model):
    # Janela móvel de 10 pratos
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE)
    valor_tma_seg = models.FloatField()
    calculado_em = models.DateTimeField(auto_now_add=True)
    
    # Auditabilidade: guarda o ID do último prato deste lote
    ultimo_prato_id = models.UUIDField(null=True)

    class Meta:
        verbose_name = "Métrica TMA"
        ordering = ['-calculado_em']

