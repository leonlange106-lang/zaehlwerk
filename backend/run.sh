#!/usr/bin/env sh
# SQLite-DB in /share (persistent). Uvicorn lauscht auf dem Ingress-Port.
set -e
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
