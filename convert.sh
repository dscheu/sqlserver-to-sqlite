#!/bin/bash

set -e

rm -rf exports

docker pull mcr.microsoft.com/mssql/server:2022-latest

CONTAINER_NAME="sqlserver"

# Check if the container is running
if [ $(docker ps -q -f name=${CONTAINER_NAME}) ]; then
    echo "Stopping container ${CONTAINER_NAME}..."
    docker stop ${CONTAINER_NAME}
    docker rm -f ${CONTAINER_NAME}
    echo "Container ${CONTAINER_NAME} stopped."
else
    echo "Container ${CONTAINER_NAME} is not running."
fi

docker build -t sqlserver-python .

docker run -e 'ACCEPT_EULA=Y' -e 'SA_PASSWORD=YourPassword123' -p 1433:1433 --name ${CONTAINER_NAME} -v "$(pwd)/backups:/var/opt/mssql/backup" -v "$(pwd)/exports:/usr/src/app/exports" -d sqlserver-python

# Now, connect to the SQL Server instance and restore each database. Create a script to automate this process.

sleep 10

# Run the restore script
docker exec -it ${CONTAINER_NAME} /usr/src/app/restore_databases.sh

# Execute the converter script

docker exec -it ${CONTAINER_NAME} python3 /usr/src/app/export_to_sqlite.py

docker stop ${CONTAINER_NAME}
docker rm ${CONTAINER_NAME}
