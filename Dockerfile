FROM python:3.8.10-alpine

WORKDIR /app

RUN apk --no-cache add curl g++ gcc libxslt-dev linux-headers musl-dev

COPY requirements.txt ./

RUN pip install -U pip setuptools \
    && pip install -r requirements.txt \
    && echo "*/5 * * * * curl http://localhost:8000/api/update/feeds >/dev/null 2>&1" >> /etc/crontabs/root \
    && echo "0 0 1 * * curl http://localhost:8000/api/update/favicons >/dev/null 2>&1" >> /etc/crontabs/root

COPY aggregator ./aggregator/
COPY reader ./reader/
COPY gunicorn.conf.py ./

ENV FLASK_APP=aggregator.app

CMD sh -c "crond && gunicorn"

EXPOSE 8000
