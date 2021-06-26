from flask import Flask

from aggregator.api import api
from aggregator.config import Config
from aggregator.models import db
from aggregator.reader import reader


def create_app(config=Config()):
    app = Flask(__name__, static_folder='../reader')
    app.config.from_object(config)

    db.init_app(app)

    app.add_url_rule('/', 'root', lambda: app.send_static_file('index.html'))
    app.add_url_rule('/<path:path>', 'files', lambda path: app.send_static_file(path))
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(reader, url_prefix='/reader')

    return app
