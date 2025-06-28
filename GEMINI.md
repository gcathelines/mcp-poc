# Gemini Workspace

This document provides a high-level overview of the project, its structure, and key commands for developers and contributors.

## Project Overview

This project is a playground for experimenting with the Multi-Agent Conversation Platform (MCP) and LangGraph. It includes a BigQuery server that exposes data analysis tools and a LangGraph agent that uses these tools to answer questions.

## Key Technologies

*   **Python**: The primary programming language.
*   **FastMCP**: Used to create the BigQuery server.
*   **LangGraph**: Used to build the conversational agent.
*   **Google Gemini**: The language model used by the agent.
*   **Docker**: For containerizing and running the services.
*   **uv**: For Python packacage management.

## Commands

*   **Activate virtual environment**: `source .venv/bin/activate`
*   **Run BigQuery server**: `uv run src/bigquery/server.py`
*   **Run LangGraph Studio**: `langgraph dev --config ./app/langgraph.json`
*   **Run with Docker**: `docker-compose up`

## File Structure

*   `src/bigquery/server.py`: The main entry point for the BigQuery server. It defines the tools that are exposed to the agent.
*   `app/agent.py`: Defines the LangGraph agent, including the language model, tools, and graph structure.
*   `app/app.py`: A simple command-line interface for interacting with the agent.
*   `pyproject.toml`: The project's dependencies.
*   `docker-compose.yml`: Defines the services for the BigQuery server and LangGraph Studio.
*   `Dockerfile`: Used to build the Docker image for the server.
*   `GEMINI.md`: This file.
*   `README.md`: The project's README file.
