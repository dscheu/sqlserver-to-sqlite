# Stop script on error
$ErrorActionPreference = "Stop"

# Remove exports directory if it exists
if (Test-Path -Path "exports") {
    Remove-Item -Recurse -Force -Path "exports"
}

# Pull the latest SQL Server Docker image
docker pull mcr.microsoft.com/mssql/server:2022-latest

$CONTAINER_NAME = "sqlserver"

# Check if the container is running
$container = docker ps -q -f "name=$CONTAINER_NAME"
if ($container) {
    Write-Host "Stopping container $CONTAINER_NAME..."
    docker stop $CONTAINER_NAME
    docker rm -f $CONTAINER_NAME
    Write-Host "Container $CONTAINER_NAME stopped."
} else {
    Write-Host "Container $CONTAINER_NAME is not running."
}

# Build the Docker image
docker build -t sqlserver-python .

# Run the Docker container
docker run -e 'ACCEPT_EULA=Y' -e 'SA_PASSWORD=YourPassword123' -p 1433:1433 --name $CONTAINER_NAME -v "$(Get-Location)/backups:/var/opt/mssql/backup" -v "$(Get-Location)/exports:/usr/src/app/exports" -d sqlserver-python

# Sleep for 10 seconds to ensure SQL Server is fully started
Start-Sleep -Seconds 10

# Run the restore script
docker exec -it $CONTAINER_NAME /usr/src/app/restore_databases.sh

# Run the export script
docker exec -it $CONTAINER_NAME python3 /usr/src/app/export_to_sqlite.py

# Stop and remove the container
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME
