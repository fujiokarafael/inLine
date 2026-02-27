async function atualizarPainel() {
  try {
    const res = await fetch("/api/v1/monitor/pedidos/");
    const data = await res.json();

    const containers = {
      pendentes: document.getElementById("lista-pendentes"),
      preparando: document.getElementById("lista-preparando"),
      prontos: document.getElementById("lista-prontos"),
    };

    Object.values(containers).forEach((c) => (c.innerHTML = ""));

    // Pendentes: Fundo cinza bem claro, texto escuro
    data.pendentes.forEach((p) => {
      containers.pendentes.innerHTML += `
                <div class="bg-slate-50 border border-slate-100 p-5 rounded-2xl text-center font-black text-3xl text-slate-700 shadow-inner">
                    ${p.senha}
                </div>`;
    });

    // Preparando: Fundo branco, borda âmbar
    data.preparando.forEach((p) => {
      containers.preparando.innerHTML += `
                <div class="bg-white border-2 border-amber-400 p-5 rounded-2xl text-center font-black text-3xl text-amber-600 shadow-md">
                    ${p.senha}
                </div>`;
    });

    // Prontos: Card branco gigante no fundo verde
    data.prontos.forEach((p) => {
      containers.prontos.innerHTML += `
                <div class="bg-white p-8 rounded-3xl text-center shadow-lg transform scale-105 transition-all">
                    <div class="text-7xl font-black text-emerald-600 tracking-tighter">${p.senha}</div>
                    <div class="text-xs font-bold uppercase mt-2 text-slate-400">${p.tipo}</div>
                </div>`;
    });
  } catch (e) {
    console.error("Erro ao atualizar painel:", e);
  }
}

atualizarPainel();
setInterval(atualizarPainel, 5000);
