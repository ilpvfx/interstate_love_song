# Interstate Love Song

A customizeable broker for Teradici systems.

## Running

You can run a WSGI-server directly by

```shell script
python -m interstate_love_song -s [server]
```

The arguments are:

- -s, --server: can be `gunicorn`, `cherrypy` or `werkzeug`. `gunicorn` is recommended, and default. 

- --host: (default: localhost)
- -p, --port: (default: 60443).

- --fallback_sessions: In some cases, the PCOIP client might not use the cookie if the header doesn't have the correct case.
HTTP spec says header names are case insensitive, but the PCOIP-client thinks some of them should be. In those situations 
we can track the session using the `CLIENT-LOG-ID` header instead. Note that you should, if you can, get cookies running 
since that's more stable and less wasteful.

- --config: configuration file.
- --cert: SSL certificate file, SSL is not optional. (default: selfsign.crt)
- --key: SSL key file (default: selfsign.key)


### Choosing a server
The Teradici PCOIP client is very picky and particular. 
- The server must use chunked encoding (they claim it supports 
regular HTTP transmission, but it doesn't.) 
- **SSL is a must**. 
- The cookie set header must be explicitly "Set-Cookie", no
other case is allowed.

If you are on *NIX, consider Gunicorn.

CherryPy runner is a good choice for development on windows. `--fallback_sessions` might be needed when running CherryPy. 

Werkzeug seems to not work well at all. This is not because Werkzeug is bad, but because of the above reasons, something
about the communication doesn't jive with the Teradici PCOIP client.

#### Using uWSGI

*Not supported yet*

## Settings

Generate a default config with:
```shell script
python -m interstate_love_song.settings > ../settings.json
```

## Mappers
Mappers assign resources to users; in plain english, they decide which Teradici machines, if any, to present to a 
connecting client.

### SimpleMapper

The Simple Mapper is, indeed simple. It authenticates only one, common, user. It returns a given set of resources for
this user, with no special logic.

The Simple Mapper is mostly for testing and to serve as a reference implementation.

#### Generating a password hash
The username and password is stored in the settings. To provide a modicum of security over a plaintext password, we require
the password to be "pre-hashed". That way we won't store a plaintext password anywhere.

To generate a hashed password, simply call:

```shell script
python -m interstate_love_song.mapping.simple "a very long password"
```


## Requirements

- Python 3.7+
- falcon
- pytest *(for testing)*
- defusedxml
- xmldiff *(for testing)*
- beaker
- falcon_middleware_beaker
- requests
- httpretty *(for testing)*

If you want to run Gunicorn, you need gunicorn and gevent.

If you want to use the CherryPy's runner or Werkzeug, you'll need those packages as well.