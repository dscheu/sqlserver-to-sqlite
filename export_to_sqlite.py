import pyodbc
import pandas as pd
import sqlite3
import os

# Connection string to SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=master;"
    "UID=sa;"
    "PWD=YourPassword123"
)

# Connect to SQL Server
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Get list of databases
cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')")
databases = cursor.fetchall()

# Loop through each database
for db in databases:
    db_name = db[0]
    if not db_name:
        continue

    print(f"Processing database: {db_name}")

    # Connect to each database
    db_conn_str = conn_str.replace("DATABASE=master;", f"DATABASE={db_name};")
    db_conn = pyodbc.connect(db_conn_str)
    db_cursor = db_conn.cursor()

    # Get list of tables
    db_cursor.execute("SELECT name FROM sys.tables")
    tables = db_cursor.fetchall()

    # Create a SQLite database
    sqlite_file = f"exports/{db_name}.sqlite"
    if not os.path.exists('exports'):
        os.makedirs('exports')
    sqlite_conn = sqlite3.connect(sqlite_file)

    # Export each table to the SQLite database
    for table in tables:
        table_name = table[0]
        if not table_name:
            continue

        print(f"Exporting table: {table_name} from database: {db_name}")
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, db_conn)
        df.to_sql(table_name, sqlite_conn, if_exists='replace', index=False)

    # Close SQLite connection
    sqlite_conn.close()

    # Close database connection
    db_conn.close()

# Close SQL Server connection
conn.close()
