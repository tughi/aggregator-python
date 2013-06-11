import unittest
import json

import requests


SERVER = 'http://localhost:4280'

GET = requests.get
POST = requests.post
DELETE = requests.delete


def server_request(method, path, **data):
    response = method(SERVER + path, data=data)
    if response.status_code == 200:
        return json.loads(response.content)
    raise Exception(response.content, response.status_code)


def server_upload(method, path, files):
    response = method(SERVER + path, files=files)
    if response.status_code == 200:
        return json.loads(response.content)
    raise Exception(response.content, response.status_code)


class ServerTest(unittest.TestCase):
    def setUp(self):
        # make sure the are no feeds
        feeds = server_request(GET, '/api/feeds')
        if feeds:
            for feed in feeds:
                server_request(DELETE, '/api/feeds/%d' % feed['id'])

            self.assertTrue(not server_request(GET, '/api/feeds'))

    def _test_add_feed(self):
        server_request(POST, '/api/feeds', url='http://www.theverge.com/rss/index.xml')
        server_request(POST, '/api/feeds', url='http://feeds.gawker.com/gizmodo/full')
        server_request(POST, '/api/feeds', url='http://www.engadget.com/rss.xml')
        print(len(server_request(GET, '/api/entries')))

    def test_import_opml(self):
        print server_upload(POST, '/api/opml/import', files={'opml': open('subscriptions.xml', 'rb')})


if __name__ == '__main__':
    unittest.main()
