// static/js/caixa.js
let carrinho = {}; // Usamos Objeto para facilitar a contagem de quantidades

async function carregarProdutos() {
  try {
    const res = await fetch("/api/v1/pratos/"); // Alinhado com a rota padrão
    const pratos = await res.json();
    const grid = document.getElementById("grid-produtos");
    grid.innerHTML = pratos
      .map(
        (p) => `
            <button onclick="adicionar('${p.id}', '${p.nome}', ${p.preco})" 
                    class="p-4 bg-white shadow rounded-xl hover:bg-blue-50 transition-all text-left border-2 border-transparent hover:border-blue-500">
                <div class="font-bold text-gray-800">${p.nome}</div>
                <div class="text-blue-600 font-bold">R$ ${parseFloat(p.preco).toFixed(2)}</div>
            </button>
        `,
      )
      .join("");
  } catch (e) {
    console.error("Erro ao carregar menu:", e);
  }
}

function adicionar(id, nome, preco) {
  if (carrinho[id]) {
    carrinho[id].qtd += 1;
  } else {
    carrinho[id] = { nome, preco: parseFloat(preco), qtd: 1 };
  }
  renderizarCarrinho(); // Certifique-se de que essa função existe para atualizar a barra lateral
}

async function finalizarPedido(tipo) {
  const itens = Object.keys(carrinho).map((id) => ({
    prato_id: id,
    quantidade: carrinho[id].qtd,
  }));

  if (itens.length === 0) return alert("Adicione itens ao carrinho!");

  try {
    const res = await fetch("/api/v1/pedidos/criar/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo, itens }),
    });

    if (res.ok) {
      const dados = await res.json();

      // 1. Preencher dados no cupom de impressão
      document.getElementById("print-senha").innerText = dados.senha;
      document.getElementById("print-data").innerText =
        dados.criado_em || new Date().toLocaleTimeString();
      document.getElementById("print-tipo").innerText = dados.tipo;
      document.getElementById("print-total").innerText =
        `R$ ${dados.total.toFixed(2)}`;

      // 2. Gerar Tabela de Itens no Cupom
      const corpoItens = document.getElementById("print-itens-corpo");
      corpoItens.innerHTML = Object.values(carrinho)
        .map(
          (item) => `
                <tr>
                    <td class="py-1">${item.qtd}x ${item.nome}</td>
                    <td class="text-right">R$ ${(item.preco * item.qtd).toFixed(2)}</td>
                </tr>
            `,
        )
        .join("");

      // 3. Gerar QR Code (Se o elemento existir)
      const qrContainer = document.getElementById("qrcode-canvas");
      if (qrContainer) {
        qrContainer.innerHTML = "";

        // LÓGICA BLINDADA PARA CODESPACES
        let origin = window.location.origin;

        // Se o origin for localhost mas estamos no Codespaces, tentamos pegar a URL da barra de endereços
        if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
          // Tenta capturar a URL do GitHub Codespaces se ela existir
          const currentUrl = window.location.href;
          if (currentUrl.includes("app.github.dev")) {
            origin = currentUrl.split("/caixa")[0]; // Pega tudo antes de /caixa
          }
        }

        // 1. Resolvemos o domínio
        let linkFinal =
          dados.status_url && !dados.status_url.includes("localhost")
            ? dados.status_url
            : origin + "/acompanhamento/" + dados.id;

        // 2. Garantimos a barra final (Trailing Slash)
        if (!linkFinal.endsWith("/")) {
          linkFinal += "/";
        }

        // 3. Geramos o QR Code
        new QRCode(qrContainer, {
          text: linkFinal,
          width: 128,
          height: 128,
          correctLevel: QRCode.CorrectLevel.H,
        });

        console.log("URL Final do QR Code:", linkFinal);
      }

      // 4. Disparar Impressão com pequeno delay para renderizar o QR Code
      setTimeout(() => {
        window.print();
        // 5. Limpar estado
        carrinho = {};
        renderizarCarrinho();
        alert("Pedido finalizado e enviado para impressão!");
      }, 500);
    } else {
      const erro = await res.json();
      alert("Erro: " + (erro.error || "Falha ao processar pedido"));
    }
  } catch (e) {
    console.error("Erro na requisição:", e);
    alert("Erro de conexão com o servidor.");
  }
}

async function atualizarIndicadoresTMA() {
  const container = document.getElementById("tma-container");
  if (!container) return;

  try {
    const res = await fetch("/api/v1/metrica/tma-dashboard/");
    if (!res.ok) return;
    const dados = await res.json();

    container.innerHTML = dados
      .map((item) => {
        const corStatus =
          item.status === "alerta" ? "border-red-500" : "border-green-500";
        return `
                <div class="bg-gray-800 border-l-4 ${corStatus} p-3 rounded-xl min-w-[140px] shadow-lg">
                    <span class="text-[9px] block text-gray-400 font-black uppercase tracking-widest truncate">${item.prato_nome}</span>
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

document.addEventListener("DOMContentLoaded", () => {
  carregarProdutos(); // Carrega os produtos ao iniciar
  atualizarIndicadoresTMA();
  setInterval(atualizarIndicadoresTMA, 30000);
});
