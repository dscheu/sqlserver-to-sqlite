#!/bin/bash

set -e

# Define variables
SA_PASSWORD=${SA_PASSWORD:-YourPassword123}
CONTAINER_NAME=sqlserver-python

# Get the list of .bak files
bak_files=$(ls /var/opt/mssql/backup/*.bak)

# Loop through each .bak file and restore the database
for bak_file in $bak_files; do
    db_name=$(basename "$bak_file" .bak)
    echo "Restoring database: $db_name from $bak_file"

    # Get logical file names from the .bak file
    file_list=$( /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -Q "RESTORE FILELISTONLY FROM DISK = '$bak_file';" -s "," -W)

    # Debug: print the file list to understand its structure
    echo "File list for $db_name:"
    echo "$file_list"

    data_file=""
    log_file=""

    while IFS=, read -r logical_name physical_name type rest; do
        if [[ $type =~ .*D.* ]]; then
            data_file=$(echo "$logical_name" | tr -d ' ')
        elif [[ $type =~ .*L.* ]]; then
            log_file=$(echo "$logical_name" | tr -d ' ')
        fi
    done <<< "$file_list"

    if [ -z "$data_file" ] || [ -z "$log_file" ]; then
        echo "Error: Could not determine logical file names for $db_name. Skipping."
        continue
    fi

    echo "Data file: $data_file"
    echo "Log file: $log_file"

    # Restore the database using the correct logical file names
    /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P $SA_PASSWORD -Q "
    RESTORE DATABASE [$db_name]
    FROM DISK = '$bak_file'
    WITH MOVE '$data_file' TO '/var/opt/mssql/data/${db_name}.mdf',
    MOVE '$log_file' TO '/var/opt/mssql/data/${db_name}_log.ldf';
    "
done
