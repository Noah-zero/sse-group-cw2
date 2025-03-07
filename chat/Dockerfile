FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc python3-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5002

ENTRYPOINT ["/entrypoint.sh"]
