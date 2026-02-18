// static/js/producao.js

// 1. Função Global de Finalização (acessada pelo onclick)
async function finalizarItem(filaId) {
  console.log("Tentando finalizar item:", filaId);
  try {
    const res = await fetch(`/api/v1/fila/finalizar/${filaId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });

    if (res.ok) {
      console.log("Item finalizado com sucesso");
      atualizarPainel(); // Recarrega a tela
    } else {
      console.error("Erro na resposta do servidor ao finalizar");
    }
  } catch (e) {
    console.error("Falha na requisição de finalização:", e);
  }
}

// 2. Função de Atualização do Painel
async function atualizarPainel() {
  const container = document.getElementById("painel-estacoes");
  if (!container) return;

  try {
    const res = await fetch("/api/v1/fila/painel/");
    const data = await res.json();
    const pendentes = data.pendentes || [];

    // Agrupamento
    const grupos = {};
    pendentes.forEach((item) => {
      if (!grupos[item.prato_nome]) grupos[item.prato_nome] = [];
      grupos[item.prato_nome].push(item);
    });

    container.innerHTML = "";
    Object.keys(grupos)
      .sort()
      .forEach((nomePrato) => {
        const itens = grupos[nomePrato];
        const colunaHTML = `
                <div class="flex-none w-80 bg-gray-800/40 rounded-3xl flex flex-col border border-gray-700">
                    <div class="p-4 border-b border-gray-700 bg-gray-800 rounded-t-3xl flex justify-between items-center">
                        <h2 class="text-white font-black uppercase">${nomePrato}</h2>
                        <span class="bg-blue-600 text-white text-xs px-2 py-1 rounded">${itens.length}</span>
                    </div>
                    <div class="p-4 space-y-4 overflow-y-auto">
                        ${itens
                          .map(
                            (item) => `
                            <div class="bg-white rounded-2xl border-l-8 ${item.tipo === "PREFERENCIAL" ? "border-red-500" : "border-blue-500"} p-4 shadow-lg">
                                <div class="text-[10px] font-black text-gray-400 mb-2 uppercase">${item.tipo}</div>
                                <div class="text-2xl font-black text-gray-900 mb-4">#${item.pedido_id.slice(0, 4).toUpperCase()}</div>
                                <button onclick="finalizarItem('${item.fila_id}')" 
                                    class="w-full bg-gray-900 hover:bg-green-600 text-white py-3 rounded-xl font-bold transition-all">
                                    CONCLUIR
                                </button>
                            </div>
                        `,
                          )
                          .join("")}
                    </div>
                </div>`;
        container.insertAdjacentHTML("beforeend", colunaHTML);
      });
  } catch (e) {
    console.error("Erro ao atualizar painel:", e);
  }
}

// 3. Auxiliar para CSRF (Obrigatório no Django)
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

// 4. Inicialização
document.addEventListener("DOMContentLoaded", () => {
  atualizarPainel();
  setInterval(atualizarPainel, 5000);
});
