import re
import requests

matcher = re.compile('src="(//cdnjs.*)js"')

with open('../../index.html', 'r') as file:
	for line in file:
		match = matcher.search(line)
		if match:
			js_url = 'http:%sjs' % match.group(1)
			print('Downloading: ' + js_url)

			r = requests.get(js_url)
			if r.status_code != 200:
				print 'Download failed:', r.status_code 
				continue

			with open(js_url[js_url.rfind('/') + 1:], 'w') as js:
				js.write(r.content)

			map_url = 'http:%smap' % match.group(1)
			r = requests.get(map_url)
			if r.status_code != 200:
				continue

			with open(map_url[map_url.rfind('/') + 1:], 'w') as map:
				map.write(r.content)
