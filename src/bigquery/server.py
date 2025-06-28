# import ollama
from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="BigQuery COVID-19 Analysis",
    instructions="This server provides data analysis tools.",
    host="0.0.0.0",
    port=4200,
)

client = bigquery.Client()


@mcp.tool()
def get_dataset_info(project: str, dataset: str):
    """Get information about the COVID-19 dataset in BigQuery."""
    dataset_ref = client.dataset(dataset, project=project)
    dataset = client.get_dataset(dataset_ref)
    return {
        "dataset_id": dataset.dataset_id,
        "description": dataset.description,
        "location": dataset.location,
        "created": dataset.created,
        "updated": dataset.modified,
    }


@mcp.tool()
def list_tables(project: str, dataset: str):
    """List all tables in the specified dataset."""
    dataset_ref = client.dataset(dataset, project=project)
    tables = client.list_tables(dataset_ref)
    return [{"table_id": table.table_id} for table in tables]


@mcp.tool()
def get_table_schema(project: str, dataset: str, table: str):
    """Get the schema of a specific table in the dataset."""
    table = client.get_table(f"{project}.{dataset}.{table}")
    return [
        {
            "name": field.name,
            "type": field.field_type,
            "mode": field.mode,
            "description": field.description,
        }
        for field in table.schema
    ]


@mcp.tool()
def query_table(query: str):
    """Run a query on a specific table in the dataset."""
    query_job = client.query(query)
    results = query_job.result()
    return [
        {field.name: row[field.name] for field in results.schema} for row in results
    ]


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )
