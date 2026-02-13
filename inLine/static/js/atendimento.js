// atendimento.js

// --- ESTA PARTE É VITAL: Executa assim que a página carrega ---
document.addEventListener("DOMContentLoaded", () => {
  console.log("Terminal de Atendimento iniciado...");
  carregarListaPendentes();

  // Atualiza a fila automaticamente a cada 10 segundos
  setInterval(carregarListaPendentes, 10000);
});

async function carregarListaPendentes() {
  const listaDoc = document.getElementById("lista-pendentes");
  if (!listaDoc) return;

  try {
    const res = await fetch("/api/v1/fila/proximo/");
    // Se a lista vier vazia (204), limpamos a tela
    if (res.status === 204) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    const pendentes = await res.json();
    listaDoc.innerHTML = "";

    if (pendentes.length === 0) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    pendentes.forEach((p) => {
      const senha = String(p.pedido_id).slice(0, 4).toUpperCase();
      const corBorda =
        p.tipo === "PREFERENCIAL" ? "border-red-500" : "border-amber-500";

      listaDoc.innerHTML += `
                <div class="bg-slate-800 p-4 rounded-xl border-l-4 ${corBorda} mb-3 shadow-lg">
                    <div class="text-white font-black text-lg">#${senha} - ${p.prato}</div>
                    <div class="text-slate-400 text-[10px] font-bold uppercase tracking-widest">${p.tipo}</div>
                </div>`;
    });
  } catch (e) {
    console.error("Erro ao listar pendentes:", e);
    listaDoc.innerHTML =
      '<p class="text-red-500 text-sm">Erro ao conectar com o servidor.</p>';
  }
}

async function chamarProximo() {
  const btn = document.getElementById("btn-chamar");
  btn.disabled = true; // Evita cliques duplos

  try {
    const res = await fetch("/api/v1/fila/proximo/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"), // Segurança do Django
      },
    });

    if (res.status === 204) {
      alert("Não há pedidos pendentes!");
    } else if (res.ok) {
      const p = await res.json();

      // Atualiza o Painel Grande
      const senha = String(p.pedido_id).slice(0, 4).toUpperCase();
      document.getElementById("senha-display").innerText = senha;
      document.getElementById("info-adicional").innerText = p.prato;

      // Som de alerta (opcional/feedback visual)
      console.log("Chamando senha: " + senha);

      // Atualiza a fila lateral imediatamente
      carregarListaPendentes();
    }
  } catch (e) {
    console.error("Erro ao chamar próximo:", e);
  } finally {
    btn.disabled = false;
  }
}

// Função auxiliar para o Token de Segurança do Django
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
