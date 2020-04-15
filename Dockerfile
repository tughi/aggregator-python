FROM python:2.7-alpine

WORKDIR /app

COPY requirements.txt ./

RUN apk --no-cache add gcc libxslt-dev linux-headers musl-dev \
    && pip install -r requirements.txt \
    && pip install uwsgi

COPY server.py /app/
COPY aggregator /app/aggregator/
COPY reader /app/reader/

CMD uwsgi --http :8000 --chdir /app --pythonpath /app --wsgi-file server.py

EXPOSE 8000
