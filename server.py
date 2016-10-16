from bottle import Bottle, run, static_file
from aggregator.api import api
from aggregator.reader import reader
import os


# uWSGI support
os.chdir(os.path.dirname(__file__))

server = Bottle()
server.mount('/api', api)
server.mount('/reader', reader)

# uWSGI support
application = server


@server.route('/<path:path>')
def web(path):
    return static_file(path, 'reader')


@server.route('/')
def entries():
    return static_file('index.html', 'reader')


if __name__ == '__main__':
    run(application, host='127.0.0.1', port=8000)
