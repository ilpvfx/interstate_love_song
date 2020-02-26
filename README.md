# Interstate Love Song

A customizeable broker for Teradici systems.

## Running

You can run a WSGI-server directly by

```shell script
python -m interstate_love_song -s [server]
```

The arguments are:

- -s, --server: can be `gunicorn`, `cherrypy` or `werkzeug`. `gunicorn` is recommended, and default. 

- -p, --port: default is 60443, setting this overrides the settings JSON.

- --fallback_sessions: For some reasons, the PCOIP client might not use the cookie if it doesn't like the HTTP transport,
we suspect this is when the connection is not kept alive. In those situations we can track the session using the 
`CLIENT-LOG-ID` header instead. Note that you should, if you can, get cookies running since that's more stable and less 
wasteful.

- --config: configuration file.
- --cert: SSL certificate file
- --key: SSL key file


### Chosing a server
CherryPy runner is a good choice for development on windows. Werkzeug seems to not work well at all. 

The Teradici PCOIP client is very picky and particular. The server must use chunked encoding (they claim it supports 
regular HTTP transmission, but it doesn't.) 

The server should preferably support `Connection: Keep-Alive`, or cookies might not be set properly. 

## Settings

Generate a default config with:
```shell script
python -m interstate_love_song.settings > ../settings.json
```

## Requirements

- Python 3.7+
- falcon
- gunicorn
- pytest *(for testing)*
- defusedxml
- xmldiff *(for testing)*
- beaker
- falcon_middleware_beaker

If you want to use the CherryPy's runner or Werkzeug, you'll need those packages as well.