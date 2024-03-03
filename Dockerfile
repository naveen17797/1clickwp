# stage 1: build angular
FROM node:18-alpine as ui
WORKDIR /app/ui
COPY ui .
RUN npm i && npm run build


# stage 2: build main app.
FROM python:3.10-alpine
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# copy all except ui directory.
COPY deps deps
COPY images images
COPY models models
COPY routers routers
COPY main.py main.py
COPY utils.py utils.py
COPY --from=ui /app/ui/dist/ui ui/dist/ui
EXPOSE 8000
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--timeout-keep-alive", "30000"]