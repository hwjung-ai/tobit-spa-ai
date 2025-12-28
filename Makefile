api-venv:
	cd apps/api && python -m venv .venv

api-install:
	cd apps/api && .venv/Scripts/pip install -r requirements.txt

api-dev:
	cd apps/api && .venv/Scripts/python -m uvicorn main:app --reload --port 8000

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

status:
	git status
