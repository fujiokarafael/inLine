import uuid
from django.db import models


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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    status = models.CharField(max_length=20, choices=Status.choices)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "tipo", "created_at"]),
        ]


# =========================
# PRATO (CATÁLOGO)
# =========================

class Prato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    tempo_preparo_seg = models.IntegerField()

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
        RETIRADO = "RETIRADO"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="filas")
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT, null=True)

    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    usado_em_metrica = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["prato", "status", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]


# =========================
# MÉTRICA (TMA)
# =========================

class TMA(models.Model):
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    tempo_medio_seg = models.FloatField()  # segundos
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]

