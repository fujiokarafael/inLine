(function () {
  let ultimaSenhaExibida = null;

  const verificarPedidosProntos = async () => {
    try {
      const response = await fetch(
        "/api/v1/monitor/pedidos/?t=" + new Date().getTime(),
        {
          cache: "no-store",
        },
      );
      const data = await response.json();

      // Se a lista não estiver vazia, pegamos o primeiro item (que é o mais recente)
      if (data.prontos && data.prontos.length > 0) {
        const ultimoPedido = data.prontos[0];

        if (String(ultimoPedido.id) !== String(ultimaSenhaExibida)) {
          const display = document.getElementById("display-senha");
          if (display) display.innerText = `#${ultimoPedido.senha}`;

          ultimaSenhaExibida = ultimoPedido.id;
          console.log("Senha atualizada para:", ultimoPedido.senha);
        }
      }
    } catch (error) {
      console.error("Erro na busca:", error);
    }
  };

  setInterval(verificarPedidosProntos, 3000);
  verificarPedidosProntos();
})();
