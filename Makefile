SHELL := /bin/bash

clean:
	@cd docker; docker compose down

network-test:
	@cd docker; docker compose up --build --detach
	@echo "network test running"

logs:
	@cd docker; docker compose logs --follow

bash:
	@cd docker; docker compose exec ait-server bash
