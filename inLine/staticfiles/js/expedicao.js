alert("O ARQUIVO FOI CARREGADO!");
(function () {
  console.log("Sistema de Expedição Inicializado...");

  let ultimaSenhaExibida = null;

  // Função de exibição protegida
  const exibirSenha = (senha) => {
    const display = document.getElementById("display-senha");
    if (display) {
      display.innerText = `#${senha}`;
    }
  };

  // Função principal de busca
  const verificarPedidosProntos = async () => {
    console.log("Verificando API em:", new Date().toLocaleTimeString()); // ISSO DEVE APARECER A CADA 3 SEG
    try {
      // A URL com timestamp garante que o cache do navegador seja ignorado
      const response = await fetch(
        "/api/v1/monitor/pedidos/?t=" + new Date().getTime(),
        {
          method: "GET",
          headers: {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Pragma: "no-cache",
            Expires: "0",
          },
        },
      );

      const data = await response.json();

      if (data.prontos && data.prontos.length > 0) {
        const ultimoPedido = data.prontos[0];

        if (String(ultimoPedido.id) !== String(ultimaSenhaExibida)) {
          console.log("Atualizando para senha:", ultimoPedido.senha);
          exibirSenha(ultimoPedido.senha);
          ultimaSenhaExibida = ultimoPedido.id;
        }
      }
    } catch (error) {
      console.error("Falha ao buscar pedidos:", error);
    }
  };

  // Executa imediatamente ao carregar
  verificarPedidosProntos();

  // Executa a cada 3 segundos
  setInterval(verificarPedidosProntos, 3000);
})();
