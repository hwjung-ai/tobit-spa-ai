api-venv:
	cd apps/api && python -m venv .venv

api-install:
	cd apps/api && .venv/bin/pip install -r requirements.txt

api-dev:
	cd apps/api && .venv/bin/python -m uvicorn main:app --reload --port 8000

api-lint:
	cd apps/api && .venv/bin/ruff check .

api-format:
	cd apps/api && .venv/bin/ruff format .

api-test:
	cd apps/api && .venv/bin/pytest

api-migrate:
	cd apps/api && .venv/bin/alembic upgrade head

api-worker:
	cd apps/api && .venv/bin/python run_worker.py

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

web-lint:
	cd apps/web && npm run lint

web-format:
	cd apps/web && npm run format

web-test:
	cd apps/web && npm run test

dev:
	npx concurrently --kill-others-on-fail --names "API,WORKER,WEB" --prefix-colors "blue,magenta,green" "cd apps/api && .venv/bin/python -m uvicorn main:app --reload --port 8000" "cd apps/api && .venv/bin/python run_worker.py" "cd apps/web && npm run dev:log"

status:
	git status

# Deployment commands
deploy-api:
	docker build -f docker/Dockerfile.api -t ops-api .
	docker push ops-api

deploy-web:
	docker build -f docker/Dockerfile.web -t ops-web .
	docker push ops-web

deploy-prod:
	docker-compose -f docker/docker-compose.yml up -d

deploy-staging:
	docker-compose -f docker/docker-compose.staging.yml up -d

stop:
	docker-compose -f docker/docker-compose.yml down

restart-api:
	docker-compose -f docker/docker-compose.yml restart api

restart-web:
	docker-compose -f docker/docker-compose.yml restart web

logs-api:
	docker-compose -f docker/docker-compose.yml logs -f api

logs-web:
	docker-compose -f docker/docker-compose.yml logs -f web

logs-worker:
	docker-compose -f docker/docker-compose.yml logs -f worker

clean:
	docker system prune -f
	docker volume prune -f

# Docker development
dev-docker:
	docker-compose -f docker/docker-compose.yml up --build

dev-docker-detached:
	docker-compose -f docker/docker-compose.yml up -d --build

# Kubernetes deployment (if needed)
deploy-k8s:
	kubectl apply -f k8s/

undeploy-k8s:
	kubectl delete -f k8s/

# Database migration
db-migrate:
	docker-compose -f docker/docker-compose.yml exec api python -m alembic upgrade head

db-seed:
	docker-compose -f docker/docker-compose.yml exec api python scripts/seed.py

db-reset:
	docker-compose -f docker/docker-compose.yml down -v
	docker-compose -f docker/docker-compose.yml up -d postgres
	sleep 10
	$(MAKE) db-migrate
	$(MAKE) db-seed

# Monitoring and health checks
health-check:
	curl -f http://localhost:8000/health || echo "API health check failed"
	curl -f http://localhost:3000 || echo "Web health check failed"

monitoring:
	docker-compose -f docker/docker-compose.yml exec api python -c "import sys; sys.path.append('/app'); from apps.api.scripts.health import check_health; print(check_health())"

# Backup and restore
backup-db:
	docker-compose -f docker/docker-compose.yml exec postgres pg_dump -U ops_user ops_orchestration > backup_$(date +%Y%m%d_%H%M%S).sql

restore-db:
	docker-compose -f docker/docker-compose.yml exec -T postgres psql -U ops_user ops_orchestration < backup.sql

# Performance testing
load-test:
	docker-compose -f docker/docker-compose.yml run --rm load-test

# Security scan
security-scan:
	docker scan ops-api
	docker scan ops-web

# Documentation generation
docs-api:
	cd docs && mkdocs build

docs-serve:
	cd docs && mkdocs serve

# Test in docker
test-docker-api:
	docker-compose -f docker/docker-compose.yml run --rm api pytest

test-docker-web:
	docker-compose -f docker/docker-compose.yml run --rm web npm test

test-docker-e2e:
	docker-compose -f docker/docker-compose.yml run --rm e2e pytest
