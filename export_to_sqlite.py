import pyodbc
import pandas as pd
import sqlite3
import os
import csv

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
cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
databases = cursor.fetchall()

def get_foreign_keys(cursor, schema_name, table_name):
    cursor.execute(f"""
        SELECT
            fk.name AS FK_name,
            tp.name AS parent_table,
            cp.name AS parent_column,
            tr.name AS referenced_table,
            cr.name AS referenced_column
        FROM
            sys.foreign_keys AS fk
        INNER JOIN
            sys.foreign_key_columns AS fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN
            sys.tables AS tp ON fkc.parent_object_id = tp.object_id
        INNER JOIN
            sys.columns AS cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
        INNER JOIN
            sys.tables AS tr ON fkc.referenced_object_id = tr.object_id
        INNER JOIN
            sys.columns AS cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
        WHERE
            tp.name = '{table_name}' AND tp.schema_id = (SELECT schema_id FROM sys.schemas WHERE name = '{schema_name}')
    """)
    return cursor.fetchall()

def get_table_schema(cursor, schema_name, table_name):
    cursor.execute(f"""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema_name}' AND TABLE_NAME = '{table_name}'
    """)
    return cursor.fetchall()

def export_constraints_to_csv(db_cursor, db_name, schema_name, mode='w'):
    db_cursor.execute(f"""
        SELECT
            tc.TABLE_SCHEMA,
            tc.TABLE_NAME,
            kcu.COLUMN_NAME,
            tc.CONSTRAINT_TYPE,
            rc.UNIQUE_CONSTRAINT_SCHEMA,
            rc.UNIQUE_CONSTRAINT_NAME,
            kcu2.TABLE_NAME AS REFERENCED_TABLE_NAME,
            kcu2.COLUMN_NAME AS REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
        LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS kcu
            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        LEFT JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS rc
            ON tc.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS kcu2
            ON rc.UNIQUE_CONSTRAINT_NAME = kcu2.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = '{schema_name}'
        ORDER BY tc.TABLE_SCHEMA, tc.TABLE_NAME, tc.CONSTRAINT_TYPE, kcu.COLUMN_NAME
    """)
    constraints = db_cursor.fetchall()

    csv_file = f"exports/{db_name}_constraints.csv"
    with open(csv_file, mode=mode, newline='') as file:
        writer = csv.writer(file)
        if mode == 'w':  # Write header only if mode is 'w'
            writer.writerow([
                "Schema Name", "Table Name", "Constraint Type",
                "Column Name", "Combined Schema, Table and Column Name",
                "Referenced Schema", "Referenced Table Name", "Referenced Column Name",
                "Combined Referenced Schema, Table and Column Name"
            ])
        for constraint in constraints:
            (schema, table, column, constraint_type,
             ref_schema, ref_constraint, ref_table, ref_column) = constraint
            combined_table_name = f"{schema}.{table}"
            combined_column_name = f"{combined_table_name}.{column}"
            combined_ref_name = f"{ref_schema}.{ref_table}.{ref_column}" if ref_schema and ref_table and ref_column else ''
            writer.writerow([
                schema, table, constraint_type,
                column, combined_column_name,
                ref_schema, ref_table, ref_column,
                combined_ref_name
            ])

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

    # Get list of tables with schema
    db_cursor.execute("""
        SELECT s.name AS schema_name, t.name AS table_name
        FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        ORDER BY s.name, t.name
    """)
    tables = db_cursor.fetchall()

    # Extract unique schemas
    unique_schemas = set(schema_name for schema_name, _ in tables)

    # Create a SQLite database
    sqlite_file = f"exports/{db_name}.sqlite"
    if not os.path.exists('exports'):
        os.makedirs('exports')
    sqlite_conn = sqlite3.connect(sqlite_file)
    # Enable foreign key constraints
    sqlite_conn.execute("PRAGMA foreign_keys = ON")
    sqlite_conn.commit()

    sqlite_cursor = sqlite_conn.cursor()

    # Export constraints to CSV once with header for the first schema
    first_schema = True
    for schema_name in unique_schemas:
        mode = 'w' if first_schema else 'a'
        export_constraints_to_csv(db_cursor, db_name, schema_name, mode=mode)
        first_schema = False

    # Export each table to the SQLite database
    for schema_name, table_name in tables:
        full_table_name = f"{schema_name}.{table_name}"
        sqlite_table_name = full_table_name  # Use the full name with periods
        print(f"Exporting table: {full_table_name} from database: {db_name} to SQLite table: {sqlite_table_name}")

        # Get table schema
        schema = get_table_schema(db_cursor, schema_name, table_name)

        # Create table statement with foreign keys
        create_table_sql = f'CREATE TABLE "{sqlite_table_name}" ('
        primary_keys = []
        for column in schema:
            column_name, data_type, char_length = column
            if data_type.lower() in ["varchar", "nvarchar", "char"]:
                create_table_sql += f'"{column_name}" {data_type.upper()}({char_length}), '
            else:
                create_table_sql += f'"{column_name}" {data_type.upper()}, '
            if "PRIMARY KEY" in data_type.upper():
                primary_keys.append(column_name)

        foreign_keys = get_foreign_keys(db_cursor, schema_name, table_name)
        print(f"Foreign keys for {full_table_name}: {foreign_keys}")
        for fk in foreign_keys:
            fk_name, parent_table, parent_column, referenced_table, referenced_column = fk
            referenced_table_name = f"{schema_name}.{referenced_table}"
            create_table_sql += (f'FOREIGN KEY("{parent_column}") REFERENCES "{referenced_table_name}"("{referenced_column}"), ')

        if primary_keys:
            create_table_sql += f'PRIMARY KEY ({", ".join([f"{key}" for key in primary_keys])}), '

        create_table_sql = create_table_sql.rstrip(", ") + ");"
        print(f"Create table SQL: {create_table_sql}")
        # Activate foreign keys during table creation
        sqlite_conn.execute("PRAGMA foreign_keys = ON")
        sqlite_cursor.execute(create_table_sql)
        sqlite_conn.commit()  # Explicitly commit after creating the table

        # Export data
        query = f"SELECT * FROM [{schema_name}].[{table_name}]"
        df = pd.read_sql(query, db_conn)
        # Deactivate foreign keys during data import
        sqlite_conn.execute("PRAGMA foreign_keys = OFF")
        df.to_sql(sqlite_table_name, sqlite_conn, if_exists='append', index=False)
        sqlite_conn.commit()  # Explicitly commit after inserting the data

    # Close SQLite connection
    sqlite_conn.close()

    # Close database connection
    db_conn.close()

# Close SQL Server connection
conn.close()
