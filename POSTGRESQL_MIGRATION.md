# VetSync PostgreSQL Migration Guide

Date: 2026-04-30

## Configuration

VetSync now reads the production database from `DATABASE_URL`.

Example `.env`:

```env
FLASK_ENV=production
DATABASE_URL=postgresql://username:password@localhost:5432/vetsync_db
AUTO_CREATE_DB=false
```

For hosted platforms that provide `postgres://...`, the app normalizes it to `postgresql://...` for SQLAlchemy compatibility.

## Install Dependencies

```powershell
pip install -r requirements.txt
```

The PostgreSQL driver and migration tooling are now included:

```text
psycopg2-binary
Flask-Migrate
```

## Create PostgreSQL Database

Using `psql`:

```sql
CREATE DATABASE vetsync_db WITH ENCODING 'UTF8';
CREATE USER vetsync_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE vetsync_db TO vetsync_user;
\c vetsync_db
GRANT ALL ON SCHEMA public TO vetsync_user;
ALTER SCHEMA public OWNER TO vetsync_user;
```

Then set:

```env
DATABASE_URL=postgresql://vetsync_user:strong_password_here@localhost:5432/vetsync_db
```

## Run Migrations

Set Flask entrypoint:

```powershell
$env:FLASK_APP="run.py"
```

Initialize migrations once:

```powershell
flask db init
```

Run `flask db init` only once. If the `migrations/` folder already exists, do not run it again.

Create the first migration:

```powershell
flask db migrate -m "initial PostgreSQL schema"
```

Apply migrations:

```powershell
flask db upgrade
```

If you see this error:

```text
connection to server at "localhost", port 5432 failed: Connection refused
```

PostgreSQL is not running or is not installed on the machine. Start PostgreSQL first, confirm port `5432` is open, then rerun:

```powershell
flask db migrate -m "initial PostgreSQL schema"
flask db upgrade
```

If you see this error:

```text
permission denied for schema public
```

Use a dedicated schema owned by the application user:

```powershell
$env:PGPASSWORD="your_password_here"
psql -U vetsync_user -d vetsync_db -c "CREATE SCHEMA IF NOT EXISTS vetsync AUTHORIZATION vetsync_user;"
psql -U vetsync_user -d vetsync_db -c "ALTER ROLE vetsync_user SET search_path TO vetsync;"
```

Then rerun:

```powershell
flask db migrate -m "initial PostgreSQL schema"
flask db upgrade
```

For later schema changes, run:

```powershell
flask db migrate -m "describe change"
flask db upgrade
```

## Existing SQLite Data

If you need to move existing SQLite data to PostgreSQL, use one of these options.

Recommended option with `pgloader`:

```bash
pgloader sqlite:///absolute/path/to/vetsync.db postgresql://vetsync_user:strong_password_here@localhost:5432/vetsync_db
```

Manual option:

1. Export each SQLite table to CSV.
2. Apply PostgreSQL schema with `flask db upgrade`.
3. Import CSV files with PostgreSQL `COPY`.
4. Reset sequences for serial primary keys.

Example sequence reset:

```sql
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1), true) FROM users;
SELECT setval(pg_get_serial_sequence('bookings', 'id'), COALESCE(MAX(id), 1), true) FROM bookings;
```

## Deployment Notes

- Use `FLASK_ENV=production`.
- Keep `AUTO_CREATE_DB=false` in production. Use migrations instead of `db.create_all()`.
- Ensure the database and client encoding are UTF-8.
- Do not commit `.env`.
- Run `flask db upgrade` as part of deployment before starting the web process.
