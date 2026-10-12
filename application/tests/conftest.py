import pytest

from aggregator.app import create_app
from aggregator.models import db


class TestConfig(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_LOG_LEVEL = None


@pytest.fixture
def app():
    app = create_app(TestConfig())

    with app.app_context():
        db.create_all()
        yield app
