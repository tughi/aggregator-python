import logging

import click
from flask import Flask

from aggregator import content
from aggregator.api import api
from aggregator.config import Config
from aggregator.models import db
from aggregator.reader import reader

logging.basicConfig()


def create_app(config=Config()):
    app = Flask(__name__, static_folder='../reader')
    app.config.from_object(config)

    if app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    db.init_app(app)

    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    app.add_url_rule('/<path:path>', 'files', lambda path: app.send_static_file(path))
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(reader, url_prefix='/reader')

    @app.cli.command('restore')
    @click.argument('file', type=click.File('r'))
    def restore(file):
        content.restore(file)

    return app
