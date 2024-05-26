ARG PYTHON_VERSION=3.9.6
FROM python:${PYTHON_VERSION}-slim as base
COPY ./init-user-db.sh /docker-entrypoint-initdb.d/init-user-db.sh

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

COPY . .

EXPOSE 11000
EXPOSE 5432

CMD python app.py


