import uuid
from django.db import models

class Pedido(models.Model):
    class Tipo(models.TextChoices):
        NORMAL = "NORMAL"
        PREFERENCIAL = "PREFERENCIAL"

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE"
        PRODUCAO = "PRODUCAO"
        FINALIZADO = "FINALIZADO"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    status = models.CharField(max_length=15, choices=Status.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "tipo", "created_at"]),
        ]


class FilaPrato(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    usado_em_metrica = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["finished_at", "usado_em_metrica"]),
        ]


class TMA(models.Model):
    tinicial = models.DateTimeField()
    tfinal = models.DateTimeField()
    valor_ms = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
