// static/js/producao.js

async function refreshPainel() {
  try {
    // 1. Busca os dados da API
    const res = await fetch("/api/v1/fila/painel/");
    if (!res.ok) return;

    const data = await res.json();

    // 2. Seleciona o container CORRETO (conforme seu HTML)
    const container = document.getElementById("cards-container");
    const counter = document.getElementById("counter-pendente");

    if (!container) {
      console.error("Erro: Elemento 'cards-container' não encontrado no HTML.");
      return;
    }

    // Atualiza o contador de pedidos no topo
    if (counter) counter.innerText = data.pendentes.length;

    // 3. Limpa o container para reconstruir a lista
    container.innerHTML = "";

    if (data.pendentes.length === 0) {
      container.innerHTML = `
                <div class="text-gray-500 border-2 border-dashed border-gray-800 p-10 rounded-2xl w-full text-center">
                    Aguardando novos pedidos...
                </div>`;
      return;
    }

    // 4. Mapeia os dados para os Cards
    data.pendentes.forEach((item) => {
      const isPref = item.tipo === "PREFERENCIAL";
      const card = `
                <div class="flex-none w-80 bg-white rounded-2xl shadow-2xl overflow-hidden border-t-8 ${isPref ? "border-red-500" : "border-blue-500"} transition-all">
                    <div class="p-6">
                        <div class="flex justify-between items-start mb-4">
                            <span class="bg-gray-100 text-gray-700 text-[10px] font-black px-2 py-1 rounded-md uppercase tracking-wider">${item.tipo}</span>
                            <span class="text-gray-400 text-xs font-mono">${item.tempo_espera} min</span>
                        </div>
                        
                        <h2 class="text-2xl font-black text-gray-900 leading-tight mb-2 uppercase">${item.prato_nome}</h2>
                        <p class="text-gray-400 text-xs font-bold mb-6 italic">PEDIDO: #${item.pedido_id.slice(0, 4).toUpperCase()}</p>
                        
                        <button onclick="iniciarPreparo('${item.fila_id}')" 
                            class="w-full bg-gray-900 hover:bg-green-600 text-white py-4 rounded-xl font-bold transition-all transform active:scale-95 shadow-lg flex items-center justify-center gap-2">
                            <span>CONCLUIR</span>
                        </button>
                    </div>
                </div>`;
      container.insertAdjacentHTML("beforeend", card);
    });
  } catch (error) {
    console.error("Erro ao atualizar o painel de produção:", error);
  }
}

/**
 * Função para finalizar o prato
 */
async function iniciarPreparo(filaId) {
  try {
    const res = await fetch(`/api/v1/fila/finalizar/${filaId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });

    if (res.ok) {
      refreshPainel(); // Atualiza a tela na hora
    }
  } catch (err) {
    console.error("Erro ao finalizar:", err);
  }
}

// Função para o Token CSRF do Django
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

// Inicia o Polling (atualiza a cada 5 segundos)
refreshPainel();
setInterval(refreshPainel, 5000);
