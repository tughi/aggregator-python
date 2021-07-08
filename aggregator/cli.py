import logging

import click
from flask import Blueprint

from aggregator import content
from aggregator import sync

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

blueprint = Blueprint('cli', __name__, cli_group=None)


@blueprint.cli.command('restore')
@click.argument('file', type=click.File('r'))
def restore(file):
    content.restore(file)


@blueprint.cli.command('sync')
def start_sync():
    sync.start()
