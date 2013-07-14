from bottle import Bottle, run, static_file
from aggregator.reader import reader

server = Bottle()
server.mount('/reader', reader)


@server.route('/<path:path>')
def web(path):
    return static_file(path, 'reader')


@server.route('/')
def entries():
    return static_file('index.html', 'reader')


if __name__ == '__main__':
    run(server, port=8000)
