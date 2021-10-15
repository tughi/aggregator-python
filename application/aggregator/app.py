import logging

from flask import Flask

from aggregator import api
from aggregator import cli
from aggregator import graphql
from aggregator import reader
from aggregator.config import Config
from aggregator.models import db

logging.basicConfig()


def create_app(config=Config()):
    app = Flask(__name__)
    app.config.from_object(config)

    if config.SQLALCHEMY_ENGINE_LOG_LEVEL:
        logging.getLogger('sqlalchemy.engine').setLevel(config.SQLALCHEMY_ENGINE_LOG_LEVEL)

    db.init_app(app)

    app.register_blueprint(api.blueprint, url_prefix='/api')
    app.register_blueprint(cli.blueprint)
    app.register_blueprint(graphql.blueprint, url_prefix='/')
    app.register_blueprint(reader.blueprint, url_prefix='/v1/reader/api')

    return app
