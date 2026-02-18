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

async function atualizarIndicadoresTMA() {
  const container = document.getElementById("tma-container");
  if (!container) return;

  try {
    const res = await fetch("/api/v1/metrica/tma-dashboard/");
    const dados = await res.json();

    container.innerHTML = dados
      .map((item) => {
        const corStatus =
          item.status === "alerta"
            ? "text-red-500 border-red-500/20"
            : "text-green-500 border-green-500/20";

        return `
                <div class="bg-gray-800 border ${corStatus} p-3 rounded-xl min-w-[140px] shadow-lg">
                    <span class="text-[9px] block text-gray-400 font-black uppercase tracking-widest">${item.prato_nome}</span>
                    <div class="flex items-baseline gap-1">
                        <span class="text-xl font-black text-white">${item.tma_minutos}</span>
                        <span class="text-[10px] font-bold text-gray-500 uppercase">min</span>
                    </div>
                </div>
            `;
      })
      .join("");
  } catch (e) {
    console.error("Erro ao carregar TMA:", e);
  }
}

// Inicia a atualização
document.addEventListener("DOMContentLoaded", () => {
  atualizarIndicadoresTMA();
  setInterval(atualizarIndicadoresTMA, 30000); // Atualiza a cada 30 segundos
});
