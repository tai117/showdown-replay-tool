.PHONY: build run fetch analyze test clean

# Construir imagen Docker
build:
	docker compose build

# Ejecutar fetch por defecto
run:
	docker compose up

# Fetch con argumentos personalizados
fetch:
	docker compose run --rm showdown-tool fetch $(ARGS)

# Analizar metagame
analyze:
	docker compose run --rm showdown-tool analyze $(ARGS)

# Ejecutar suite de pruebas
test:
	docker compose run --rm showdown-tool pytest

# Limpiar caché y artefactos
clean:
	rm -rf ./data/replays/* ./data/structured/* ./data/reports/* ./data/state.json
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
