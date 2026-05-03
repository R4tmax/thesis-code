import os
import yaml
from google.cloud import bigquery


def generate_yaml_schema():
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("BQ_DATASET_ID")

    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT table_name, column_name, data_type 
        FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        ORDER BY table_name, ordinal_position
    """

    results = client.query(query).result()

    tables_dict = {}
    for row in results:
        t_name = f"{dataset_id}.{row.table_name}"
        if t_name not in tables_dict:
            tables_dict[t_name] = {
                "name": t_name,
                "description": f"Auto-generated schema for {t_name}",
                "columns": []
            }

        tables_dict[t_name]["columns"].append(f"| {row.column_name} | {row.data_type} |")

    yaml_output = {"tables": []}
    for t_name, data in tables_dict.items():
        schema_string = "\n".join(data["columns"])
        yaml_output["tables"].append({
            "name": data["name"],
            "description": data["description"],
            "schema": schema_string
        })

    with open("tables.yaml", "w", encoding="utf-8") as f:
        yaml.dump(yaml_output, f, allow_unicode=True, sort_keys=False)

    print("Successfully generated tables.yaml from live BigQuery schema!")


if __name__ == "__main__":
    generate_yaml_schema()