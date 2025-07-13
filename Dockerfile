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

# Install dependencies
ENV DOCKERVERSION=28.3.1

RUN  apt-get update && apt-get install -y curl && curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKERVERSION}.tgz \
  && tar xzvf docker-${DOCKERVERSION}.tgz --strip 1 \
                 -C /usr/local/bin docker/docker \
  && rm docker-${DOCKERVERSION}.tgz

ENTRYPOINT ["/code/entrypoint.sh"]