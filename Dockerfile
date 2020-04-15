FROM python:2.7-alpine

WORKDIR /app

COPY requirements.txt ./

RUN apk --no-cache add curl gcc libxslt-dev linux-headers musl-dev \
    && pip install -r requirements.txt \
    && pip install uwsgi \
    && echo "*/5 * * * * curl http://localhost:8000/api/update/feeds >/dev/null 2>&1" >> /etc/crontabs/root \
    && echo "0 0 1 * * curl http://localhost:8000/api/update/favicons >/dev/null 2>&1" >> /etc/crontabs/root

COPY server.py /app/
COPY aggregator /app/aggregator/
COPY reader /app/reader/

CMD sh -c "crond && uwsgi --http :8000 --chdir /app --pythonpath /app --wsgi-file server.py"

EXPOSE 8000
