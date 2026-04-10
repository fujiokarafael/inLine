// atendimento.js

// Mantém o registro de quais pedidos já foram impressos para não repetir
let pedidosProntosConhecidos = new Set();

document.addEventListener("DOMContentLoaded", () => {
  console.log("Terminal de Atendimento iniciado...");
  carregarListaPendentes();

  // 1. Atualiza a fila visual de espera a cada 10 segundos
  setInterval(carregarListaPendentes, 10000);

  // 2. SOLUÇÃO 3: Vigia a API para imprimir quando a cozinha finalizar TUDO
  // Verificação a cada 7 segundos para garantir agilidade na entrega
  setInterval(monitorarPedidosParaImpressao, 7000);
});

async function carregarListaPendentes() {
  const listaDoc = document.getElementById("lista-pendentes");
  if (!listaDoc) return;

  try {
    const res = await fetch("/api/v1/fila/proximo/");
    if (res.status === 204 || !res.ok) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    const pendentes = await res.json();
    listaDoc.innerHTML = "";

    if (!pendentes || pendentes.length === 0) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    pendentes.forEach((p) => {
      const senha = String(p.pedido_id).toUpperCase().slice(0, 4);
      const corBorda =
        p.tipo === "PREFERENCIAL" ? "border-red-500" : "border-amber-500";

      listaDoc.innerHTML += `
        <div class="bg-slate-800 p-4 rounded-xl border-l-4 ${corBorda} mb-3 shadow-lg flex justify-between items-center">
            <div>
                <div class="text-white font-black text-2xl">#${senha}</div>
                <div class="text-[10px] font-bold uppercase tracking-widest text-slate-400">${p.tipo}</div>
            </div>
            <div class="text-slate-500 text-xs font-mono">${p.criado_em}</div>
        </div>`;
    });
  } catch (e) {
    console.error("Erro ao listar pendentes:", e);
  }
}

// LÓGICA DE AUTO-IMPRESSÃO (SÓ QUANDO A COZINHA TERMINA TUDO)
// atendimento.js

let primeiraCargaRealizada = false; // TRAVA DE SEGURANÇA

async function monitorarPedidosParaImpressao() {
  try {
    const res = await fetch("/api/v1/monitor/pedidos/");
    if (!res.ok) return;
    const data = await res.json();

    // Se for a primeira vez que carregamos a página, apenas populamos o Set
    // sem disparar a impressora.
    if (!primeiraCargaRealizada) {
      data.prontos.forEach((pedido) => {
        pedidosProntosConhecidos.add(pedido.senha);
      });
      primeiraCargaRealizada = true;
      console.log(
        "Sistema de auto-impressão sincronizado. Aguardando novos pedidos...",
      );
      return; // Sai da função sem imprimir nada
    }

    // Nas cargas seguintes (após os primeiros 7 segundos), ele imprime o que for novo
    data.prontos.forEach((pedido) => {
      if (!pedidosProntosConhecidos.has(pedido.senha)) {
        console.log(`💡 Novo pedido completo: #${pedido.senha}. Imprimindo...`);
        dispararImpressaoFisica(pedido);
        pedidosProntosConhecidos.add(pedido.senha);
      }
    });
  } catch (e) {
    console.error("Erro no monitor de auto-impressão:", e);
  }
}

async function chamarProximo() {
  const btn = document.getElementById("btn-chamar");
  const display = document.getElementById("senha-display");

  btn.disabled = true;

  try {
    const res = await fetch("/api/v1/fila/proximo/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    });

    if (res.status === 204) {
      alert("Não há pedidos pendentes!");
    } else if (res.ok) {
      const p = await res.json();

      // APENAS atualiza o visual do painel de chamada (Digital)
      display.innerText = p.senha;
      display.classList.add("animate-bounce"); // Pequeno efeito visual ao chamar
      setTimeout(() => display.classList.remove("animate-bounce"), 1000);

      carregarListaPendentes();
    }
  } catch (e) {
    console.error("Erro ao chamar próximo:", e);
  } finally {
    btn.disabled = false;
  }
}

function dispararImpressaoFisica(p) {
  const confSenha = document.getElementById("conf-senha");
  const confItens = document.getElementById("conf-itens");

  if (confSenha && confItens) {
    confSenha.innerText = p.senha;

    // Gerar lista de checklist para conferência
    const itensHTML = p.itens
      ? p.itens
          .map(
            (i) =>
              `<div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #eee; padding: 4px 0;">
        <span>[ ] ${i.quantidade}x ${i.nome}</span>
      </div>`,
          )
          .join("")
      : "Conferir itens no sistema";

    confItens.innerHTML = itensHTML;

    // Dispara a impressão silenciosa
    window.print();
  }
}

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
