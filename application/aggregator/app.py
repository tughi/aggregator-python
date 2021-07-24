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
    app = Flask(__name__, static_folder='../reader')
    app.config.from_object(config)

    if app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    db.init_app(app)

    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    app.add_url_rule('/<path:path>', 'files', lambda path: app.send_static_file(path))

    app.register_blueprint(api.blueprint, url_prefix='/api')
    app.register_blueprint(cli.blueprint)
    app.register_blueprint(graphql.blueprint, url_prefix='/')
    app.register_blueprint(reader.blueprint, url_prefix='/reader')

    return app
