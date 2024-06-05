FROM mcr.microsoft.com/mssql/server:2022-latest

USER root

# Install Python and necessary packages
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get install -y python3-dev && \
    apt-get install -y libsqlite3-dev && \
    pip3 install pyodbc pandas

# Copy the scripts into the container
COPY restore_databases.sh /usr/src/app/restore_databases.sh
COPY export_to_sqlite.py /usr/src/app/export_to_sqlite.py

# Make the restore script executable
RUN chmod +x /usr/src/app/restore_databases.sh

# Switch back to the default non-root user
USER mssql

# Set the working directory
WORKDIR /usr/src/app
