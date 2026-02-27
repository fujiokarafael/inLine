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

    // Se for 204 ou não estiver OK, limpamos a lista e saímos
    if (res.status === 204 || !res.ok) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    // Só tentamos ler o JSON se houver conteúdo
    const pendentes = await res.json();
    listaDoc.innerHTML = "";

    if (!pendentes || pendentes.length === 0) {
      listaDoc.innerHTML =
        '<p class="text-slate-500 italic text-sm">Nenhum pedido na fila.</p>';
      return;
    }

    pendentes.forEach((p) => {
      // Extrai a senha dos 4 primeiros caracteres do UUID
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
    // Aqui capturamos o erro de SyntaxError: Unexpected end of JSON input
    console.error("Erro ao listar pendentes:", e);
  }
}

async function chamarProximo() {
  const btn = document.getElementById("btn-chamar");
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

      // 1. Atualiza o display visual com a senha vinda do servidor
      document.getElementById("senha-display").innerText = p.senha;

      // 2. Dispara a lógica de impressão (usando o JSON completo)
      imprimirCupomAtendente(p);

      // 3. Atualiza a lista lateral
      carregarListaPendentes();
    }
  } catch (e) {
    console.error("Erro ao chamar próximo:", e);
  } finally {
    btn.disabled = false;
  }
}

function imprimirCupomAtendente(p) {
  // Monta o texto para a impressora ou console
  const itensTexto = p.itens
    .map((i) => `${i.quantidade}x ${i.nome}`)
    .join("\n");

  const cupom = `
============================
   ENTREGA DE PRODUTOS
============================
SENHA: ${p.senha}
TIPO:  ${p.tipo}
HORA:  ${p.hora_impressao}
----------------------------
ITENS DO PEDIDO:
${itensTexto}
----------------------------
TOTAL DE ITENS: ${p.total_itens}
============================
  `;

  console.log(cupom);
  // Se quiser abrir a caixa de impressão do navegador:
  // prepararJanelaImpressao(cupom);
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
