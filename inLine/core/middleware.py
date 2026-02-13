import datetime
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

class LicensingMiddleware:
    """
    Middleware de Licenciamento Offline.
    Valida a LICENSE_KEY e a data de expiração antes de processar operações críticas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Definir caminhos protegidos (ex: criação de pedidos e captura de fila)
        # Ignoramos caminhos de admin ou estáticos para não travar a manutenção
        protected_paths = ['/api/v1/pedidos/', '/api/v1/fila/']
        
        if any(request.path.startswith(path) for path in protected_paths):
            if not self._is_license_valid():
                # Retorna 402 Payment Required conforme exigido no requisito 6
                return JsonResponse(
                    {
                        "error": "Licença Inválida ou Expirada",
                        "message": "Operação bloqueada. Por favor, regularize sua licença para continuar operando offline."
                    }, 
                    status=402
                )

        return self.get_response(request)

    def _is_license_valid(self) -> bool:
        """
        Lógica de validação baseada em settings locais.
        Em um cenário real, aqui haveria uma decodificação de um JWT ou Hash RSA.
        """
        license_key = getattr(settings, 'LICENSE_KEY', None)
        expiry_date = getattr(settings, 'LICENSE_EXPIRY', None) # Formato date object

        if not license_key:
            return False

        # Validação de Data Local vs Data de Expiração
        if expiry_date and datetime.date.today() > expiry_date:
            return False

        return True
