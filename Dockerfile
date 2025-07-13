FROM python:3.10.12-slim-bullseye

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./entrypoint.sh /code/entrypoint.sh
RUN pip install --no-cache-dir -r /code/requirements.txt

COPY ./app /code/app
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]