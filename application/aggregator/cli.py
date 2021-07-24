import logging

import click
from flask import Blueprint

from aggregator import content
from aggregator import engine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

blueprint = Blueprint('cli', __name__, cli_group=None)


@blueprint.cli.command('restore')
@click.argument('file', type=click.File('r'))
def restore(file):
    content.restore(file)


@blueprint.cli.command('update-feeds')
def update_feeds():
    logger.info("Updating feeds")
    engine.update_feeds()


@blueprint.cli.command('update-favicons')
def update_favicons():
    logger.info("Updating favicons")
    engine.update_favicons()
