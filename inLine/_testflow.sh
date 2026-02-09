#!/bin/bash
set -e

BASE="http://127.0.0.1:8000/api"

echo "=============================="
echo " 🚀 INICIANDO TESTFLOW"
echo "=============================="

sleep 1

# ============================
# HEALTHCHECK
# ============================
echo "🔎 Verificando servidor..."
curl -s "$BASE/" >/dev/null || {
  echo "❌ Servidor não responde em $BASE"
  exit 1
}

# ============================
# CRIAR PRATOS
# ============================
echo "🍽️ Criando pratos..."

P1=$(curl -s -X POST "$BASE/pratos/" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Pastel de carne",
    "preco": "10.00",
    "tempo_preparo_seg": 90
  }')

P2=$(curl -s -X POST "$BASE/pratos/" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Pastel de queijo",
    "preco": "9.00",
    "tempo_preparo_seg": 80
  }')

PRATO1_ID=$(echo "$P1" | jq -r '.id')
PRATO2_ID=$(echo "$P2" | jq -r '.id')

echo "✅ Pratos criados:"
echo " - Pastel carne: $PRATO1_ID"
echo " - Pastel queijo: $PRATO2_ID"

# ============================
# CRIAR PEDIDO
# ============================
echo "🧾 Criando pedido no caixa..."
ORDER=$(curl -s -X POST "$BASE/orders/" \
  -H "Content-Type: application/json" \
  -d "{
    \"tipo\": \"NORMAL\",
    \"itens\": [
      {\"prato_id\": \"$PRATO1_ID\", \"quantidade\": 2},
      {\"prato_id\": \"$PRATO2_ID\", \"quantidade\": 1}
    ]
  }")

ORDER_ID=$(echo "$ORDER" | jq -r '.id')
echo "✅ Pedido criado: $ORDER_ID"

# ============================
# FUNÇÃO PARA PROCESSAR FILA DE UM PRATO
# ============================
process_prato() {
  local PRATO_ID=$1
  local PRATO_NOME=$2

  echo ""
  echo "📊 Painel cozinha - $PRATO_NOME"

  while true; do
    # Pegar próximo item pendente
    NEXT=$(curl -s -X GET "$BASE/pratos/$PRATO_ID/next/")
    FILA_ID=$(echo "$NEXT" | jq -r '.fila_id // empty')

    if [[ -z "$FILA_ID" ]]; then
      echo "✅ Todos os itens de $PRATO_NOME foram processados."
      break
    fi

    echo "➡ Próximo item da fila: $FILA_ID"

    # Iniciar produção
    echo "🚀 Iniciando produção do item $FILA_ID..."
    curl -s -X POST "$BASE/cozinha/iniciar/$FILA_ID/" -H "Content-Type: application/json" | jq .

    # Finalizar produção
    echo "✅ Finalizando produção do item $FILA_ID..."
    curl -s -X POST "$BASE/cozinha/finalizar/$FILA_ID/" -H "Content-Type: application/json" | jq .
  done
}

# ============================
# PROCESSAR TODOS OS PRATOS
# ============================
process_prato "$PRATO1_ID" "Pastel carne"
process_prato "$PRATO2_ID" "Pastel queijo"

echo ""
echo "=============================="
echo " 🎉 TESTFLOW FINALIZADO COM SUCESSO"
echo "=============================="
