FROM python:3.13.2-alpine3.21
WORKDIR /backend
COPY . /backend

ENV PORT=8000

RUN apk add gcc build-base \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir poetry==2.0.1 \
  && pip install uvicorn \
  && poetry config virtualenvs.create false \
  && poetry install


COPY . /backend

ENTRYPOINT ["/backend/entrypoint.sh"]

