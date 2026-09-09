.PHONY: bootstrap test build

bootstrap:
	npm install
	cd services/widget-bff && uv sync --dev

test:
	npm run lint:web
	npm run test:web
	cd services/widget-bff && uv run pytest

build:
	npm run build:web
	docker build -t amul-widget-bff:local services/widget-bff
	docker build -f apps/widget-web/Dockerfile -t amul-widget-web:local .
