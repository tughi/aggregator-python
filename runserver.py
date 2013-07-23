from bottle import Bottle, run, static_file
from aggregator.api import api
from aggregator.reader import reader

server = Bottle()
server.mount('/api', api)
server.mount('/reader', reader)


@server.route('/<path:path>')
def web(path):
    return static_file(path, 'reader')


@server.route('/')
def entries():
    return static_file('index.html', 'reader')


if __name__ == '__main__':
    run(server, host='0.0.0.0', port=8000)
