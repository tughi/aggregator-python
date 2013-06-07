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


class ServerTest(unittest.TestCase):
    def setUp(self):
        # make sure the are no feeds
        feeds = server_request(GET, '/feeds')
        if feeds:
            for feed in feeds:
                server_request(DELETE, '/feeds/%d' % feed['id'])

            self.assertTrue(not server_request(GET, '/feeds'))

    def test_add_feed(self):
        server_request(POST, '/feeds', url='http://www.theverge.com/rss/index.xml')
        server_request(POST, '/feeds', url='http://tughi.com/feed')


if __name__ == '__main__':
    unittest.main()
