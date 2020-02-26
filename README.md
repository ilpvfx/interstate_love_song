# Interstate Love Song

A customizeable broker for Teradici systems.

## Running

You can run a WSGI-server directly by

```shell script
python -m interstate_love_song -s [server]
```

The arguments are:

- -s, --server: can be `gunicorn`, `cherrypy` or `werkzeug`. `gunicorn` is recommended, and default. 
Setting this overrides the settings JSON.

- -p, --port: default is 60443, setting this overrides the settings JSON.


### Chosing a server
CherryPy runner is a good choice for development on windows. Werkzeug seems iffy. 

The Teradici PCOIP client is very picky and particular. The server must use chunked encoding (they claim it supports 
regular HTTP transmission, but it doesn't.) 

The server should preferably support `Connection: Keep-Alive`, or cookies might not be set properly. 

## Settings

TBD

## Requirements

- Python 3.7+
- falcon
- gunicorn
- pytest *(for testing)*
- defusedxml
- xmldiff *(for testing)*
- beaker

If you want to use the CherryPy's runner or Werkzeug, you'll need those packages as well.