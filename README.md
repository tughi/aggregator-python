# Aggregator

Python based feed reader/aggregator.

Planned features:
- Support for RSS and Atom feeds ✔
- Entry filtering support
- Feed aggregation / syndication
- OPML import ✔
- JSON-based API ✔
- Web client ✔
- Mobile web client ✔
- Android client

### Usage

The easiest way to launch Aggregator is to use docker-compose together with either docker or podman.

	docker-compose up --build

The database is configured through `DATABASE_URL` in an `.env` file.

Ports and a PostgreSQL container can be added in a `docker-compose.override.yaml`:

	services:
	  nginx:
	    ports:
	      - 8080:8080
	  database:
	    image: postgres:18
	    environment:
	      POSTGRES_PASSWORD: secret
	    volumes:
	      - database:/var/lib/postgresql
	volumes:
	  database:

and use `DATABASE_URL=postgresql://postgres:secret@database`.

### Web Client Screenshots

![Feeds](screenshots/web-feeds.png)

![Reader](screenshots/web-reader.png)

### License

Aggregator is free software: you can redistribute it and/or modify
it under the terms of the [GNU General Public License](http://www.gnu.org/licenses/gpl.txt) as
published by the Free Software Foundation, either version 3 of the License, or (at your option) any
later version.
