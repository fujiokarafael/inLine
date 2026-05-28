// static/js/producao.js

let modoEdicao = false; // Controle de estado Global

// ==========================================
// 1. FLUXO DE PRODUÇÃO
// ==========================================

async function iniciarItem(filaId) {
  try {
    const res = await fetch(`/api/v1/fila/${filaId}/iniciar/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });
    if (res.ok) atualizarPainel();
  } catch (e) {
    console.error("Falha na requisição de início:", e);
  }
}

async function finalizarItem(filaId) {
  try {
    const res = await fetch(`/api/v1/fila/${filaId}/finalizar/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });
    if (res.ok) atualizarPainel();
  } catch (e) {
    console.error("Falha na requisição de finalização:", e);
  }
}

async function atualizarPainel() {
  // BLOQUEIO CRÍTICO: Se estiver editando, não recarregue a tela de produção!
  if (modoEdicao) return;

  const container = document.getElementById("painel-estacoes");
  if (!container) return;

  try {
    const res = await fetch("/api/v1/fila/painel/");
    if (!res.ok) return;

    const data = await res.json();
    const pendentes = data.pendentes || [];
    const grupos = {};

    pendentes.forEach((item) => {
      if (!grupos[item.prato_nome]) grupos[item.prato_nome] = [];
      grupos[item.prato_nome].push(item);
    });

    container.innerHTML = "";
    const listaPratos = Object.keys(grupos).sort();

    if (listaPratos.length === 0) {
      container.innerHTML = `<div class="w-full text-center py-20 text-slate-400 font-bold uppercase tracking-widest text-sm">Nenhum prato na fila.</div>`;
      return;
    }

    listaPratos.forEach((nomePrato) => {
      const itens = grupos[nomePrato];
      const colunaHTML = `
        <div class="flex-none w-80 bg-slate-100 rounded-[2rem] flex flex-col border border-slate-200 shadow-sm overflow-hidden animate-card">
            <div class="p-4 bg-white border-b border-slate-200 flex justify-between items-center">
                <h2 class="text-slate-800 font-black uppercase tracking-tight text-sm truncate max-w-[180px]">${nomePrato}</h2>
                <span class="bg-slate-900 text-white text-xs font-black px-2.5 py-1 rounded-full">${itens.length}</span>
            </div>
            
            <div class="p-4 space-y-4 overflow-y-auto custom-scrollbar flex-1 max-h-[calc(100vh-180px)]">
                ${itens
                  .map((item) => {
                    const ehPreferencial = item.tipo === "PREFERENCIAL";
                    const emPreparo = item.status_item === "EM_PRODUCAO";
                    let cardBg = "bg-white border-slate-200";
                    let botaoHTML = "";

                    if (emPreparo) {
                      cardBg = "bg-amber-50/70 border-amber-300 animate-pulse";
                      botaoHTML = `<button onclick="finalizarItem('${item.fila_id}')" class="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all shadow-md shadow-green-100">✓ CONCLUIR</button>`;
                    } else {
                      botaoHTML = `<button onclick="iniciarItem('${item.fila_id}')" class="w-full bg-slate-900 hover:bg-blue-600 text-white py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all">🎛 COZINHAR</button>`;
                    }

                    return `
                    <div class="${cardBg} border rounded-2xl p-4 shadow-sm transition-all duration-300">
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md ${ehPreferencial ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}">${item.tipo}</span>
                            <span class="text-[9px] font-bold text-slate-400">🕒 ${item.tempo_espera} min</span>
                        </div>
                        <div class="text-2xl font-black text-slate-900 mb-4 tracking-tighter">#${item.senha}</div>
                        <div class="mt-2">${botaoHTML}</div>
                    </div>`;
                  })
                  .join("")}
            </div>
        </div>`;
      container.insertAdjacentHTML("beforeend", colunaHTML);
    });
  } catch (e) {
    console.error("Erro ao atualizar painel:", e);
  }
}

// ==========================================
// 2. FLUXO DE EDIÇÃO DE CARDÁPIO
// ==========================================

function toggleModoEdicao() {
  modoEdicao = !modoEdicao;
  const btn = document.getElementById("btn-modo-edicao");

  // Muda o estilo visual do botão
  if (modoEdicao) {
    btn.classList.add("bg-amber-100", "text-amber-700", "border-amber-300");
    btn.innerText = "Sair da Edição";
    carregarMenu(); // Desenha a tela de cardápio
  } else {
    btn.classList.remove("bg-amber-100", "text-amber-700", "border-amber-300");
    btn.innerText = "Editar Cardápio";
    atualizarPainel(); // Volta a desenhar a fila de produção
  }
}

// Essa função busca a lista de pratos no banco e os renderiza no painel central
async function carregarMenu() {
  const container = document.getElementById("painel-estacoes");
  container.innerHTML = `<div class="w-full text-center py-20 text-slate-400 animate-pulse font-bold uppercase tracking-widest text-sm">Carregando Cardápio...</div>`;

  try {
    // Certifique-se que o caminho '/api/v1/pratos/' exista e chame sua ListPratosAPIView
    const res = await fetch("/api/v1/pratos/");
    const pratos = await res.json();

    let html = pratos
      .map(
        (prato) => `
      <div class="flex-none w-64 bg-white rounded-[2rem] flex flex-col border border-slate-200 shadow-sm overflow-hidden animate-card">
          <div class="p-6">
              <h2 class="text-slate-800 font-black uppercase tracking-tight text-lg mb-1 truncate">${prato.nome}</h2>
              <div class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Estoque: <span class="${prato.estoque < 5 ? "text-red-500" : "text-slate-700"}">${prato.estoque} un</span></div>
              
              <div class="text-2xl font-black text-blue-600 tracking-tighter mb-4">R$ ${parseFloat(prato.preco).toFixed(2)}</div>
              
              <button onclick="abrirModalEdicao('${prato.id}', '${prato.nome}', '${prato.preco}', '${prato.estoque}')" 
                  class="w-full bg-slate-100 hover:bg-amber-400 hover:text-amber-900 text-slate-600 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all">
                  ✏️ Editar
              </button>
          </div>
      </div>
    `,
      )
      .join("");

    container.innerHTML = html;
  } catch (e) {
    console.error(e);
    container.innerHTML = `<div class="text-red-500 w-full text-center py-20 font-bold">Erro ao carregar cardápio.</div>`;
  }
}

function abrirModalEdicao(id, nome, preco, estoque) {
  document.getElementById("edit-id").value = id;
  document.getElementById("edit-nome").value = nome;
  document.getElementById("edit-preco").value = parseFloat(preco).toFixed(2);
  document.getElementById("edit-estoque").value = estoque;
  document.getElementById("modal-edicao").classList.remove("hidden");
}

function fecharModal() {
  document.getElementById("modal-edicao").classList.add("hidden");
}

async function salvarEdicao() {
  const id = document.getElementById("edit-id").value;
  const dados = {
    nome: document.getElementById("edit-nome").value,
    preco: document.getElementById("edit-preco").value,
    estoque: document.getElementById("edit-estoque").value,
  };

  try {
    const res = await fetch(`/api/v1/pratos/editar/${id}/`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"), // CORREÇÃO AQUI (nome da função)
      },
      body: JSON.stringify(dados),
    });

    if (res.ok) {
      fecharModal();
      carregarMenu(); // Atualiza a tela após salvar
    } else {
      alert("Erro ao salvar o prato. Verifique os valores digitados.");
    }
  } catch (e) {
    console.error(e);
  }
}

// ==========================================
// 3. UTILITÁRIOS E INICIALIZAÇÃO
// ==========================================

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener("DOMContentLoaded", () => {
  atualizarPainel();
  setInterval(atualizarPainel, 5000);
});
