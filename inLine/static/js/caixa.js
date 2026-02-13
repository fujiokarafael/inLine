// static/js/caixa.js
let carrinho = [];

async function carregarProdutos() {
  const res = await fetch("/v1/pratos/"); // Rota que lista pratos ativos
  const pratos = await res.json();
  const grid = document.getElementById("grid-pratos");
  grid.innerHTML = pratos
    .map(
      (p) => `
        <button onclick="adicionar('${p.id}', '${p.nome}', ${p.preco})" class="p-4 bg-white shadow rounded-lg hover:bg-blue-50">
            <div class="font-bold">${p.nome}</div>
            <div class="text-blue-600">R$ ${p.preco}</div>
        </button>
    `,
    )
    .join("");
}

function adicionar(id, nome, preco) {
  carrinho.push({ prato_id: id, nome, preco });
  renderCarrinho();
}

async function finalizarPedido(tipo) {
  if (carrinho.length === 0) return alert("Carrinho vazio!");

  const payload = {
    tipo: tipo, // 'NORMAL' ou 'PREFERENCIAL'
    itens: carrinho.map((i) => ({ prato_id: i.prato_id, quantidade: 1 })),
  };

  const res = await fetch("/v1/pedidos/criar/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.status === 201) {
    alert("Pedido Criado!");
    carrinho = [];
    renderCarrinho();
  } else if (res.status === 402) {
    alert("LICENÇA EXPIRADA. Procure o administrador.");
  }
}
