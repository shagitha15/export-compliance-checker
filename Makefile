.PHONY: install run-server run-client test lint clean

install:
	pip install -r server/requirements.txt
	cd client && npm install

run-server:
	cd server && uvicorn main:app --reload --port 8000

run-client:
	cd client && npm run dev

test: test-server test-client

test-server:
	cd server && pytest tests/ -v

test-client:
	cd client && npm test

lint:
	ruff check server/
	cd client && npm run lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
