import uuid
from django.db import models



class FilaPrato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT)

    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDENTE", "PENDENTE"),
            ("EM_PRODUCAO", "EM_PRODUCAO"),
            ("RETIRADO", "RETIRADO"),
        ],
        default="PENDENTE",
    )

    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    usado_em_metrica = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["prato", "status", "created_at"]),
        ]


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

    total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "tipo", "created_at"]),
        ]



class FilaPrato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT)

    preco_vendido = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDENTE", "PENDENTE"),
            ("EM_PRODUCAO", "EM_PRODUCAO"),
            ("RETIRADO", "RETIRADO"),
        ],
        default="PENDENTE",
    )

    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    usado_em_metrica = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["prato", "status", "created_at"]),
        ]




class TMA(models.Model):
    tinicial = models.DateTimeField()
    tfinal = models.DateTimeField()
    valor_ms = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
