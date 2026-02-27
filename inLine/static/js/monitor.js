async function atualizarPainel() {
  const colunas = {
    pendentes: document.getElementById("lista-pendentes"),
    preparando: document.getElementById("lista-preparando"),
    prontos: document.getElementById("lista-prontos"),
  };

  try {
    const res = await fetch("/api/v1/monitor/pedidos/");
    if (!res.ok) return;
    const data = await res.json();

    // 1. LIMPEZA: Esvazia as listas antes de redesenhar para evitar duplicados
    Object.values(colunas).forEach((col) => {
      if (col) col.innerHTML = "";
    });

    // 2. RENDERIZAR RECEBIDOS (Cinza)
    data.pendentes.forEach((p) => {
      colunas.pendentes.innerHTML += `
                <div class="bg-slate-50 border border-slate-100 p-4 rounded-2xl text-center font-bold text-2xl text-slate-400 shadow-inner">
                    ${p.senha}
                </div>`;
    });

    // 3. RENDERIZAR PREPARANDO (Âmbar)
    data.preparando.forEach((p) => {
      const corTexto =
        p.tipo === "PREFERENCIAL" ? "text-red-600" : "text-amber-600";
      colunas.preparando.innerHTML += `
                <div class="bg-white border-2 border-amber-400 p-4 rounded-2xl text-center font-black text-3xl ${corTexto} shadow-md animate-pulse">
                    ${p.senha}
                </div>`;
    });

    // 4. RENDERIZAR PRONTOS (Verde/Destaque - Ajustado para Grid 2 Colunas)
    data.prontos.forEach((p) => {
      // Reduzimos o padding (p-4) e o tamanho da fonte (text-4xl) para caberem 2 por linha
      colunas.prontos.innerHTML += `
                <div class="bg-white p-4 rounded-[1.5rem] text-center shadow-xl border-b-8 border-emerald-600 transform transition-all">
                    <div class="text-4xl font-black text-emerald-600 tracking-tighter">${p.senha}</div>
                    <div class="text-[9px] font-bold text-slate-400 uppercase mt-1 tracking-widest">${p.tipo}</div>
                </div>`;
    });
  } catch (e) {
    console.error("Erro ao atualizar monitor:", e);
  }
}

// Inicialização
atualizarPainel();
setInterval(atualizarPainel, 5000); // Atualiza a cada 5 segundos
