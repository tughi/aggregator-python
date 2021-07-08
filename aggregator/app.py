import logging

from flask import Flask

from aggregator.api import blueprint as api
from aggregator.cli import blueprint as cli
from aggregator.config import Config
from aggregator.models import db
from aggregator.reader import blueprint as reader

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
    app.register_blueprint(cli)
    app.register_blueprint(reader, url_prefix='/reader')

    return app
