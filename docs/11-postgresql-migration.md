# PostgreSQL Migration

## Мақсат

PhishGuard енді SQLite local demo режимінен бөлек PostgreSQL-пен де жұмыс істей алады.
Schema migration `Alembic` арқылы басқарылады.

## Қажетті тәуелділіктер

```bash
python -m pip install -r requirements.txt
```

Маңызды пакеттер:

- `alembic`
- `psycopg[binary]`

## `.env` үлгісі

```env
DATABASE_URL=postgresql+psycopg://phishguard:phishguard@localhost:5432/phishguard
```

## Алғашқы инициализация

```bash
python scripts/db_upgrade.py
```

Немесе:

```bash
alembic upgrade head
```

Legacy `SQLite` базасы бар болса, `python scripts/db_upgrade.py` backup жасап, жаңа schema-ға автоматты көшіреді.

## Қолданыстағы кестелер

- `emails`
- `scan_runs`
- `scan_results`
- `url_findings`

## Маңызды ереже

SQLite қолданылса, schema автоматты түрде жасалады.
PostgreSQL қолданылса, migration міндетті.

## Келесі migration шығару

```bash
alembic revision --autogenerate -m "add new table"
alembic upgrade head
```

## Диплом үшін позициялау

- Local MVP: `SQLite`
- Defensible architecture: `PostgreSQL + SQLAlchemy + Alembic`
- Schema versioning бар
- Болашақтағы multi-user және reporting query-лерге дайын
