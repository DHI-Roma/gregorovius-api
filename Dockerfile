FROM python:3.13.2-alpine3.21
WORKDIR /backend
COPY . /backend

RUN apk add gcc build-base \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir poetry==2.0.1 \
  && pip install uvicorn \
  && poetry config virtualenvs.create false \
  && poetry install


COPY . /backend

CMD ["poetry", "run", "uvicorn", "app:main", "--port", "8000", "--host", "0.0.0.0", "--workers", "2"]

