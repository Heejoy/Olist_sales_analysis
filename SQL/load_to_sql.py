from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, types

# ---------------------------------------------------------------
# Connection settings 
# ---------------------------------------------------------------
SERVER = r"localhost\MSSQLSERVER04"         
DATABASE = "olist"
DRIVER = "ODBC Driver 18 for SQL Server"    

conn_str = (
    f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
    "Trusted_Connection=yes;TrustServerCertificate=yes;"
)
engine = create_engine(
    "mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str),
    fast_executemany=True,
)

# ---------------------------------------------------------------
# Which file goes into which table
# ---------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
CLEANED = BASE / "Data" / "Cleaned_data"

FILES = {
    "customers_clean.xlsx": "customers",
    "sellers_clean.xlsx": "sellers",
    "products_clean.xlsx": "products",
    "orders_customer_unique_id.xlsx": "orders_clean",
    "order_items_clean.xlsx": "order_items",
    "order_payments.xlsx": "order_payments",
}


# ---------------------------------------------------------------
# Text columns get a fixed width (needed later for fast joins)
# ---------------------------------------------------------------
def text_types(df):
    out = {}
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            width = int(df[col].astype(str).str.len().max())
            out[col] = types.NVARCHAR(width)
    return out


# ---------------------------------------------------------------
# Read each Excel file and write it to SQL Server
# ---------------------------------------------------------------
for file_name, table_name in FILES.items():
    df = pd.read_excel(CLEANED / file_name)
    if file_name == "products_clean.xlsx":
        df = df.rename(columns={df.columns[0]: "product_id"})
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",    
        index=False,
        dtype=text_types(df),
        chunksize=10000,
    )
    print(f"{table_name}: {len(df):,} rows loaded")

print("Done.")
