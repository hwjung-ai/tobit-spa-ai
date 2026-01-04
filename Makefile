api-venv:
	cd apps/api && python -m venv .venv

api-install:
	cd apps/api && .venv/Scripts/pip install -r requirements.txt

api-dev:
	cd apps/api && .venv/Scripts/python -m uvicorn main:app --reload --port 8000

api-lint:
	cd apps/api && .venv/Scripts/ruff check .

api-format:
	cd apps/api && .venv/Scripts/ruff format .

api-test:
	cd apps/api && .venv/Scripts/pytest

api-migrate:
	cd apps/api && .venv/Scripts/alembic upgrade head

api-worker:
	cd apps/api && .venv/Scripts/python run_worker.py

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
	npx concurrently --kill-others-on-fail --names "API,WORKER,WEB" --prefix-colors "blue,magenta,green" "cd apps\api && .venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000" "cd apps\api && .venv\Scripts\python.exe run_worker.py" "cd apps\web && npm run dev:log"

status:
	git status
