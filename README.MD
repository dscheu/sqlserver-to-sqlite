# MS SQL Server to sqlite

This tooling converts MS SQL Server backups to sqlite databases.

## Prerequisites

Install docker on your system.

## Instructions

Move your `*.bak` files to `./backups/*.bak`.

On Macos / Linux:

```
./convert.sh
```

On Windows:

```
.\convert.ps1
```

The script will start a MS SQL Server docker container. Restore all the databases from the backup files in the backups folder and then writes all tables into a `./exports/*.sqlite` file per logical database.

## License

This code is released under the [MIT License](https://opensource.org/licenses/MIT).
