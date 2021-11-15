FROM tiangolo/uvicorn-gunicorn-fastapi:python3.6-2020-12-19

WORKDIR /backend
COPY . /backend

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir poetry==1.0.0 \
  && pip install uvicorn \
  && poetry config virtualenvs.create false \
  && poetry install --no-dev \
  && pip uninstall --yes poetry

RUN sed -i "s/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=1/g" /etc/ssl/openssl.cnf
RUN echo 'asdf' > /backend/.db-version

COPY . /backend

