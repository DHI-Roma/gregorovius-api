#!/bin/sh

poetry run uvicorn app:main --port ${PORT} --host 0.0.0.0 --workers 2