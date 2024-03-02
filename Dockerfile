FROM python:3.10-alpine
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD [ "python", "-m uvicorn main:app --timeout-keep-alive 30000" ]