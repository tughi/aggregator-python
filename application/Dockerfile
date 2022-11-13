FROM python:3.8-alpine

WORKDIR /app

RUN apk --no-cache add curl g++ gcc libxslt-dev linux-headers musl-dev postgresql-dev

COPY requirements.txt ./

RUN pip install -U pip setuptools \
    && pip install -r requirements.txt

COPY aggregator ./aggregator/
COPY gunicorn.conf.py ./

ENV FLASK_APP=aggregator.app

RUN adduser -D -h /app -u 1000 abuser

COPY crontab ./
RUN crontab ./crontab

USER abuser

CMD sh -c "gunicorn"

EXPOSE 8000
