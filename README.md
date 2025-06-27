# My MCP Playground :)

### Activate venv:
source .venv/bin/activate

### Running Server:
uv run src/bigquery/server.py 
entrypoint: http://localhost:4200/mcp

### Running Inspector:
mcp dev ./src/bigquery/server.py 

### Ollama things
ollama serve ->  run ollama
ollama pull mistral -> pull mistral model

### Langgraph Studio
langgraph dev --config ./app/langgraph.json

### LangSmith
https://smith.langchain.com/

dont forget to put the .env :D