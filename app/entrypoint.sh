#!/bin/sh
set -e
cd /code/app
alembic -c alembic.ini upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir /code
