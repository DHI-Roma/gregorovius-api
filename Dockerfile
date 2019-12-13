FROM tiangolo/uvicorn-gunicorn-fastapi:python3.6

WORKDIR /backend
COPY . /backend

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir poetry==1.0.0 \
  && pip install uvicorn \
  && poetry config virtualenvs.create false \
  && poetry install --no-dev \
  && pip uninstall --yes poetry

COPY . /backend

