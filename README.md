# Aggregator

Python based feeds reader/aggregator.

The idea behind this project is to create a replacement for Google Reader that serves one user and runs on a Raspberry Pi.

Planned features:
- [x] Support for RSS and Atom feeds
- [ ] Entry filtering support
- [ ] Feed aggregation / syndication
- [ ] OPML import / export
- [ ] JSON-based API
- [ ] Android client

### Quick Project Setup:

	# make sure virtualenv is installed
	pip install virtualenv

	# go to the project dir
	cd <proj-dir>

	# create environment
	virtualenv environment

	# activate the environment for the current terminal
	. environment/bin/activate

	# install required packages
	pip install -r requirements.txt

