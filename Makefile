.PHONY: run-langgraph run-bigquery-server

run-langgraph:
	AGENT_MODE=studio \
	langgraph dev --config ./app/langgraph.json

run-bigquery-server:
	uv run src/bigquery/server.py

run-cli:
	AGENT_MODE=cli \
	uv run app/app.py
