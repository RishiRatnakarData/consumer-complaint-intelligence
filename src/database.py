"""DuckDB serving layer and documented analytical outputs."""

from pathlib import Path

import duckdb
import pandas as pd


def build_database(df: pd.DataFrame, database_path: Path, sql_path: Path) -> dict[str, pd.DataFrame]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    connection.register("complaints_df", df)
    connection.execute("CREATE OR REPLACE TABLE complaints AS SELECT * FROM complaints_df")
    sql_text = sql_path.read_text(encoding="utf-8")
    connection.execute(sql_text)
    outputs = {
        "monthly_kpis": connection.execute("SELECT * FROM monthly_kpis ORDER BY received_month").df(),
        "company_benchmark": connection.execute("SELECT * FROM company_benchmark ORDER BY complaint_count DESC").df(),
        "product_issue_rank": connection.execute("SELECT * FROM product_issue_rank WHERE issue_rank <= 3 ORDER BY product, issue_rank").df(),
    }
    connection.close()
    return outputs

