let carrinho = {};
let modoEdicao = false;
let pratosCache = [];
let processandoPedido = false;

// Função para obter o CSRF Token do elemento HTML
function getCsrfToken() {
  return document.getElementById("config").getAttribute("data-csrf");
}

async function carregarMenu() {
  try {
    const res = await fetch("/api/v1/pratos/");
    pratosCache = await res.json();
    const grid = document.getElementById("grid-produtos");

    grid.innerHTML = pratosCache
      .map((p) => {
        const estoqueVal = p.estoque ?? 0;
        const precoVal = parseFloat(p.preco) || 0;
        const esgotado = estoqueVal <= 0;

        const acaoClique = modoEdicao
          ? `abrirModalEdicao('${p.id}', '${p.nome}', ${precoVal}, ${estoqueVal})`
          : esgotado
            ? ""
            : `adicionarAoCarrinho('${p.id}', '${p.nome}', ${precoVal})`;

        return `
            <button onclick="${acaoClique}" 
                    ${esgotado && !modoEdicao ? "disabled" : ""}
                    class="relative p-6 rounded-2xl shadow-sm border-2 transition-all text-left flex flex-col h-full group 
                    ${esgotado && !modoEdicao ? "bg-gray-100 border-gray-200 opacity-60 cursor-not-allowed" : "bg-white"}
                    ${modoEdicao ? "border-amber-200 bg-amber-50/30" : !esgotado ? "border-transparent hover:border-blue-500 hover:shadow-xl" : ""}">
                ${modoEdicao ? '<span class="absolute top-2 right-2 bg-amber-500 text-white p-1 rounded-lg text-[8px] font-black uppercase tracking-tighter">Editar</span>' : ""}
                ${esgotado && !modoEdicao ? '<span class="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-lg text-[8px] font-black uppercase tracking-tighter">Esgotado</span>' : ""}
                <p class="font-black ${esgotado && !modoEdicao ? "text-gray-400" : "text-slate-800"} uppercase tracking-tighter">${p.nome}</p>
                <div class="flex justify-between items-end mt-auto">
                    <p class="font-black text-xl">R$ ${precoVal.toFixed(2)}</p>
                    <p class="text-[10px] font-bold uppercase">Est: ${estoqueVal}</p>
                </div>
            </button>`;
      })
      .join("");
  } catch (e) {
    console.error("Erro ao carregar menu:", e);
  }
}

function adicionarAoCarrinho(id, nome, preco) {
  const prato = pratosCache.find((p) => p.id === id);
  if (!prato) return;
  const qtdNoCarrinho = carrinho[id] ? carrinho[id].qtd : 0;

  if (qtdNoCarrinho >= prato.estoque) {
    alert(`⚠️ Estoque insuficiente para ${nome}. Disponível: ${prato.estoque}`);
    return;
  }

  if (carrinho[id]) {
    carrinho[id].qtd += 1;
  } else {
    carrinho[id] = { nome, preco: parseFloat(preco), qtd: 1 };
    document.getElementById("carrinho-vazio")?.classList.add("hidden");
  }
  renderizarCarrinho();
}

function renderizarCarrinho() {
  const lista = document.getElementById("lista-carrinho");
  const totalElem = document.getElementById("total-pedido");
  const chaves = Object.keys(carrinho);

  if (chaves.length === 0) {
    lista.innerHTML =
      '<p id="carrinho-vazio" class="text-slate-300 text-center mt-20 font-bold uppercase text-xs tracking-widest">Carrinho vazio</p>';
    totalElem.innerText = "R$ 0,00";
    return;
  }

  let total = 0;
  lista.innerHTML = chaves
    .map((id) => {
      const item = carrinho[id];
      total += item.preco * item.qtd;
      return `
        <div class="flex justify-between items-center bg-slate-50 p-4 rounded-2xl border border-slate-100 shadow-sm">
            <div class="flex-1 pr-2">
                <p class="font-black text-xs text-slate-800 uppercase tracking-tighter">${item.nome}</p>
                <p class="text-[10px] font-bold text-blue-500">R$ ${item.preco.toFixed(2)}</p>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="alterarQtd('${id}', -1)" class="w-7 h-7 bg-white text-slate-600 rounded-lg flex items-center justify-center font-black shadow-sm">-</button>
                <span class="font-black text-sm w-4 text-center">${item.qtd}</span>
                <button onclick="alterarQtd('${id}', 1)" class="w-7 h-7 bg-white text-slate-600 rounded-lg flex items-center justify-center font-black shadow-sm">+</button>
            </div>
        </div>`;
    })
    .join("");
  totalElem.innerText = `R$ ${total.toFixed(2)}`;
}

function alterarQtd(id, delta) {
  if (!carrinho[id]) return;
  const prato = pratosCache.find((p) => p.id === id);
  const novaQtd = carrinho[id].qtd + delta;
  if (delta > 0 && prato && novaQtd > prato.estoque) {
    alert("⚠️ Limite de estoque atingido!");
    return;
  }
  if (novaQtd <= 0) delete carrinho[id];
  else carrinho[id].qtd = novaQtd;
  renderizarCarrinho();
}

async function finalizarPedido(tipo) {
  if (processandoPedido) return;
  const itens = Object.keys(carrinho).map((id) => ({
    prato_id: id,
    quantidade: carrinho[id].qtd,
  }));
  if (itens.length === 0) return alert("Carrinho vazio!");

  try {
    processandoPedido = true;
    const res = await fetch("/api/v1/pedidos/criar/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(), // Chamada da função utilitária
      },
      body: JSON.stringify({ tipo, itens }),
    });

    const dados = await res.json();
    if (res.ok) {
      // Lógica de preenchimento do cupom
      document.getElementById("print-senha").innerText = dados.senha;
      document.getElementById("print-data").innerText =
        dados.criado_em || new Date().toLocaleTimeString();
      document.getElementById("print-tipo").innerText = dados.tipo;
      document.getElementById("print-total").innerText =
        `R$ ${parseFloat(dados.total).toFixed(2)}`;

      const corpoItens = document.getElementById("print-itens-corpo");
      corpoItens.innerHTML = Object.values(carrinho)
        .map(
          (item) => `
                <tr><td class="py-1">${item.qtd}x ${item.nome}</td><td class="text-right">R$ ${(item.preco * item.qtd).toFixed(2)}</td></tr>
            `,
        )
        .join("");

      // QR Code
      // const qrContainer = document.getElementById("qrcode-canvas");
      // if (qrContainer) {
      //   qrContainer.innerHTML = "";
      //   let origin = window.location.origin;
      //   let linkFinal =
      //     dados.status_url && !dados.status_url.includes("localhost")
      //       ? dados.status_url
      //       : origin + "/acompanhamento/" + dados.id + "/";
      //   new QRCode(qrContainer, { text: linkFinal, width: 128, height: 128 });
      // }

      setTimeout(() => {
        window.print();
        carrinho = {};
        renderizarCarrinho();
        carregarMenu();
      }, 600);
    } else {
      alert("❌ Erro: " + (dados.error || "Falha no servidor."));
      await carregarMenu();
    }
  } catch (e) {
    console.error(e);
    alert("Erro crítico de conexão.");
  } finally {
    processandoPedido = false;
  }
}

window.onload = carregarMenu;
