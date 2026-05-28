let pedidosData = [];
let pedidosProntosConhecidos = new Set();
let pedidosProntosNaFila = new Set();
let filaImpressaoAutomatica = [];
let impressaoAutomaticaEmAndamento = false;
let primeiraCargaImpressao = false;
let fallbackFimImpressao = null;

async function carregarAtendimento() {
  const busca = document.getElementById("input-busca")?.value || "";
  const status = document.getElementById("filtro-status")?.value || "";

  const url = `/api/v1/atendimento/lista/?search=${busca}&status=${status}&t=${Date.now()}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Erro HTTP: ${res.status}`);

    const pedidos = await res.json();
    pedidosData = pedidos;
    renderizarTabela();
  } catch (e) {
    console.error("Falha crítica ao carregar atendimento:", e);
  }
}

document.addEventListener("DOMContentLoaded", carregarAtendimento);

function renderizarTabela() {
  const body = document.getElementById("tabela-pedidos-body");

  // Obtém o valor digitado na caixa de busca
  const termoBusca = (document.getElementById("input-busca")?.value || "")
    .toLowerCase()
    .trim();

  // Filtra os dados no frontend (muito mais rápido que esperar a API)
  const pedidosFiltrados = pedidosData.filter((p) => {
    // Procura o texto digitado na senha
    return String(p.senha).toLowerCase().includes(termoBusca);
  });

  if (pedidosFiltrados.length === 0) {
    if (termoBusca) {
      body.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-slate-400 font-bold uppercase tracking-widest">Nenhuma senha contendo "${termoBusca}" encontrada.</td></tr>`;
    } else {
      body.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-slate-400 font-bold uppercase tracking-widest">Nenhum pedido na fila.</td></tr>`;
    }
    return;
  }

  body.innerHTML = pedidosFiltrados
    .map((p) => {
      let badgeStatus = "";
      if (p.status === "PENDENTE") {
        badgeStatus = `<span class="bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1 rounded-full text-[10px] font-black uppercase">Aguardando Cozinha</span>`;
      } else if (p.status === "PRODUCAO") {
        badgeStatus = `<span class="bg-amber-100 text-amber-700 border border-amber-200 px-3 py-1 rounded-full text-[10px] font-black uppercase flex items-center gap-1 w-max"><span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span> Em Preparo</span>`;
      } else if (p.status === "FINALIZADO") {
        badgeStatus = `<span class="bg-green-100 text-green-700 border border-green-200 px-3 py-1 rounded-full text-[10px] font-black uppercase">Pronto para Entrega</span>`;
      } else if (p.status === "RETIRADO") {
        badgeStatus = `<span class="bg-blue-100 text-blue-700 border border-blue-200 px-3 py-1 rounded-full text-[10px] font-black uppercase">Entregue</span>`;
      } else if (p.status === "CANCELADO") {
        badgeStatus = `<span class="bg-red-100 text-red-700 border border-red-200 px-3 py-1 rounded-full text-[10px] font-black uppercase">Cancelado</span>`;
      }

      return `
        <tr class="border-b border-slate-50 hover:bg-blue-50/50 transition-colors">
            <td class="p-4 text-xs font-mono text-slate-400">${p.criado_em}</td>
            <td class="p-4 font-black text-xl text-blue-600">#${p.senha}</td>
            <td class="p-4">
                <span class="px-3 py-1 rounded-full text-[10px] font-black ${p.tipo === "PREFERENCIAL" ? "bg-red-100 text-red-600" : "bg-slate-100 text-slate-600"}">
                    ${p.tipo}
                </span>
            </td>
            <td class="p-4">
                ${badgeStatus}
            </td>
            <td class="p-4 flex gap-2 justify-center">
                <button onclick="reimprimirCaixa('${p.id}')" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl font-bold text-xs uppercase tracking-widest text-slate-600 transition-all" title="Recibo Caixa">🖨️ Caixa</button>
                <button onclick="reimprimirConferencia('${p.id}')" class="px-3 py-2 bg-amber-100 hover:bg-amber-200 rounded-xl font-bold text-xs uppercase tracking-widest text-amber-700 transition-all">📋 Montar</button> 
                
                ${
                  // NOVO: O botão de Entregar só aparece se a cozinha finalizou o pedido
                  p.status === "FINALIZADO"
                    ? `
                      <button onclick="retirarPedido('${p.id}')" 
                              class="px-4 py-2 bg-green-500 text-white hover:bg-green-600 shadow-md shadow-green-200 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all">
                          ✅ Entregar
                      </button>
                  `
                    : ""
                }

                ${
                  // O botão de cancelar continua aqui, mas não aparece se já foi entregue
                  p.status !== "CANCELADO" &&
                  p.status !== "FINALIZADO" &&
                  p.status !== "RETIRADO"
                    ? `
                      <button onclick="alterarStatus('${p.id}', 'CANCELAR')" 
                              class="px-4 py-2 bg-white text-red-500 border border-red-200 hover:bg-red-50 rounded-xl font-bold text-[10px] uppercase tracking-widest transition-all">
                          ✕ Cancelar
                      </button>
                  `
                    : ""
                }
            </td>
        </tr>
      `;
    })
    .join("");
}

// ==========================================
// FUNÇÕES DE IMPRESSÃO
// ==========================================

function reimprimirCaixa(id) {
  const p = pedidosData.find((x) => x.id === id);
  if (!p) return;

  const cli = document.getElementById("cupom-cliente");
  const conf = document.getElementById("cupom-conferencia");
  conf.classList.add("hidden");
  cli.classList.remove("hidden");

  document.getElementById("cli-senha").innerText = p.senha;
  document.getElementById("cli-data").innerText =
    p.criado_em || new Date().toLocaleTimeString();
  document.getElementById("cli-tipo").innerText = p.tipo || "NORMAL";
  document.getElementById("cli-total").innerText =
    `R$ ${parseFloat(p.total).toFixed(2)}`;

  const corpoItens = document.getElementById("cli-itens-corpo");
  corpoItens.innerHTML = p.itens
    .map(
      (item) => `
        <tr>
            <td class="py-1 uppercase text-sm">${item.qtd}x ${item.nome}</td>
            <td class="text-right py-1 text-sm">R$ ${parseFloat(item.subtotal).toFixed(2)}</td>
        </tr>
    `,
    )
    .join("");

  setTimeout(() => {
    window.print();
    cli.classList.add("hidden");
  }, 250);
}

function limparCuponsImpressao() {
  const cupomCli = document.getElementById("cupom-cliente");
  const cupomConf = document.getElementById("cupom-conferencia");
  cupomCli?.classList.add("hidden");
  cupomConf?.classList.add("hidden");
}

function prepararCupomConferencia(p) {
  const cupomCli = document.getElementById("cupom-cliente");
  const cupomConf = document.getElementById("cupom-conferencia");
  const confSenha = document.getElementById("conf-senha");
  const confItens = document.getElementById("conf-itens");

  if (!cupomCli || !cupomConf || !confSenha || !confItens) return false;

  cupomCli.classList.add("hidden");
  cupomConf.classList.remove("hidden");
  confSenha.innerText = p.senha;

  const listaItens = p.itens || p.itens_resumo || [];
  const itensHTML = listaItens
    .map((i) => {
      const quantidade = i.qtd || i.quantidade || 1;
      const nome = i.nome || i.prato_nome || "Item";
      return `
      <div style="display: flex; align-items: flex-start; border-bottom: 1px dashed #000; padding: 8px 0;">
        <span style="margin-right: 8px; font-size: 20px;">[ ]</span>
        <span style="flex: 1; font-size: 16px; font-weight: bold; text-transform: uppercase;">${quantidade}x ${nome}</span>
      </div>`;
    })
    .join("");

  confItens.innerHTML = itensHTML;
  return true;
}

function finalizarImpressaoAutomatica() {
  if (!impressaoAutomaticaEmAndamento) return;
  if (fallbackFimImpressao) {
    clearTimeout(fallbackFimImpressao);
    fallbackFimImpressao = null;
  }
  limparCuponsImpressao();
  impressaoAutomaticaEmAndamento = false;
  processarFilaImpressaoAutomatica();
}

function processarFilaImpressaoAutomatica() {
  if (impressaoAutomaticaEmAndamento || filaImpressaoAutomatica.length === 0)
    return;

  const proximoPedido = filaImpressaoAutomatica.shift();
  if (!proximoPedido) return;

  pedidosProntosNaFila.delete(proximoPedido.senha);

  const prontoParaImprimir = prepararCupomConferencia(proximoPedido);
  if (!prontoParaImprimir) {
    processarFilaImpressaoAutomatica();
    return;
  }

  impressaoAutomaticaEmAndamento = true;

  setTimeout(() => {
    window.print();
    fallbackFimImpressao = setTimeout(finalizarImpressaoAutomatica, 60000);
  }, 300);
}

function enfileirarImpressaoAutomatica(p) {
  if (!p?.senha || pedidosProntosNaFila.has(p.senha)) return;
  filaImpressaoAutomatica.push(p);
  pedidosProntosNaFila.add(p.senha);
  processarFilaImpressaoAutomatica();
}

function reimprimirConferencia(id) {
  const p = pedidosData.find((x) => x.id === id);
  if (!p) return;

  const prontoParaImprimir = prepararCupomConferencia(p);
  if (!prontoParaImprimir) return;

  setTimeout(() => {
    window.print();
    limparCuponsImpressao();
  }, 250);
}

// ==========================================
// AÇÕES DO SISTEMA (CANCELAMENTO E TOKENS)
// ==========================================

async function alterarStatus(id, acao) {
  if (
    acao === "CANCELAR" &&
    !confirm("Tem certeza que deseja cancelar o pedido?")
  )
    return;

  const url = `/api/v1/atendimento/lista/${id}/`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ acao: acao }),
    });

    if (response.ok) {
      await carregarAtendimento();
    } else {
      alert("Falha ao processar ação.");
    }
  } catch (e) {
    console.error("Erro ao processar ação:", e);
  }
}

function getCsrfToken() {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, 10) === "csrftoken" + "=") {
        cookieValue = decodeURIComponent(cookie.substring(10));
        break;
      }
    }
  }
  return cookieValue;
}

// ==========================================
// AUTO-IMPRESSÃO DE COZINHA (FILA BACKGROUND)
// ==========================================

async function monitorarPedidosParaImpressao() {
  try {
    const res = await fetch("/api/v1/monitor/pedidos/");
    if (!res.ok) return;
    const data = await res.json();

    if (!primeiraCargaImpressao) {
      data.prontos.forEach((p) => pedidosProntosConhecidos.add(p.senha));
      primeiraCargaImpressao = true;
      return;
    }

    data.prontos.forEach((p) => {
      if (!pedidosProntosConhecidos.has(p.senha)) {
        console.log(`Imprimindo automaticamente pedido pronto: #${p.senha}`);
        enfileirarImpressaoAutomatica(p);
        pedidosProntosConhecidos.add(p.senha);
        carregarAtendimento();
      }
    });
  } catch (e) {
    console.error("Erro no monitor de auto-impressão:", e);
  }
}

// Adicione junto com as outras funções de ação (perto do alterarStatus)
async function retirarPedido(id) {
  // 🔴 ATENÇÃO: Confirme se esta URL é EXATAMENTE a mesma do seu urls.py
  const url = `/api/v1/pedidos/retirar/${id}/`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    if (response.ok) {
      await carregarAtendimento();
    } else {
      // Escudo: Verifica se o Django mandou JSON ou uma página de Erro (HTML)
      const isJson = response.headers
        .get("content-type")
        ?.includes("application/json");

      if (isJson) {
        const data = await response.json();
        alert(
          `Falha ao dar baixa: ${data.detail || data.error || "Erro desconhecido."}`,
        );
      } else {
        const textoErro = await response.text();
        console.error(`Erro ${response.status} do Servidor:`, textoErro);
        alert(
          `Erro ${response.status}: Verifique o console do navegador e o terminal do VS Code.`,
        );
      }
    }
  } catch (e) {
    console.error("Erro crítico na requisição de retirada:", e);
    alert("Erro de comunicação com o servidor. A API pode estar fora do ar.");
  }
}

window.addEventListener("afterprint", finalizarImpressaoAutomatica);

setInterval(monitorarPedidosParaImpressao, 7000);
document
  .getElementById("input-busca")
  ?.addEventListener("input", renderizarTabela);
document
  .getElementById("filtro-status")
  ?.addEventListener("change", carregarAtendimento);
setInterval(carregarAtendimento, 5000);
