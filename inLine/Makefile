# Variáveis
PYTHON = python3
PIP = pip
MANAGE = manage.py

.PHONY: help install migrate superuser run clean test

help:
	@echo "Comandos disponíveis:"
	@echo "  make install    - Instala dependências, gera migrações e aplica no banco"
	@echo "  make run        - Inicia o servidor de desenvolvimento"
	@echo "  make migrate    - Gera e aplica novas migrações"
	@echo "  make superuser  - Cria um administrador para o sistema"
	@echo "  make clean      - Remove arquivos temporários e cache"

install:
	$(PIP) install -r requirements.txt
	$(PYTHON) $(MANAGE) makemigrations
	$(PYTHON) $(MANAGE) migrate
	@echo "------------------------------------------------"
	@echo "Ambiente configurado com sucesso!"

migrate:
	$(PYTHON) $(MANAGE) makemigrations
	$(PYTHON) $(MANAGE) migrate

superuser:
	$(PYTHON) $(MANAGE) createsuperuser

run:
	$(PYTHON) $(MANAGE) runserver 0.0.0.0:8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Arquivos temporários removidos."

# Atalho para resetar o banco se necessário (CUIDADO!)
reset-db:
	rm -f db.sqlite3
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	$(PYTHON) $(MANAGE) makemigrations
	$(PYTHON) $(MANAGE) migrate
	@echo "Banco de dados resetado do zero."git