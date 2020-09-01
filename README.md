    ________      _____                   _____       _____
    ____  _/________  /_____________________  /______ __  /_____ 
    ___  / __  __ \  __/  _ \_  ___/_  ___/  __/  __ `/  __/  _ \
    __/ /  _  / / / /_ /  __/  /   _(__  )/ /_ / /_/ // /_ /  __/
    /___/  /_/ /_/\__/ \___//_/    /____/ \__/ \__,_/ \__/ \___/ 
                                                                 
     ______                         ________                     
     ___  / _________   ______      __  ___/___________________ _
     __  /  _  __ \_ | / /  _ \     _____ \_  __ \_  __ \_  __ `/
     _  /___/ /_/ /_ |/ //  __/     ____/ // /_/ /  / / /  /_/ / 
     /_____/\____/_____/ \___/      /____/ \____//_ /_/_\__,  / 
                                                        /____/



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
- --gunicorn-worker-class: see gunicorn config (default: gevent)
- --gunicorn-workers: see gunicorn config (default: 2)

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


## Settings

Generate a default config with:
```shell script
python -m interstate_love_song.settings > ../settings.json
```

### Sections

The settings file is a JSON file with the following sections. Each section is its own JSON object.

#### logging

`level`: str; `INFO` or `DEBUG` (`INFO`)

#### beaker

Check out the [Beaker docs](https://beaker.readthedocs.io/en/latest/configuration.html).

`type`: str; session store type (`file`)

`data_dir`: str; session store location (`/tmp`)

#### mapper

`mapper`: dict; `{"plugin": "SimpleMapper", "settings": {}}`

`mapper.plugin`: str; name of the mapper to use (`SimpleMapper`)

`mapper.settings`: dict; mapper settings

*For an example see [SimpleMapper](#SimpleMapper)*

## Mappers
Mappers assign resources to users; in plain english, they decide which Teradici machines, if any, to present to a 
connecting client.

### SimpleMapper

The Simple Mapper is, indeed simple. It authenticates only one, common, user. It returns a given set of resources for
this user, with no special logic.

The Simple Mapper is mostly for testing and to serve as a reference implementation.

#### Settings

`username`: str; authentication user (`test`)

`password_hash`: str; authentication password, see the Simple Mapper section (`change_me`)

`resources`: Sequence[Resource]; the resources to present (`[]`)

`domains`: Sequence[str]; list of available domains

**Example Config for SimpleMapper**
For example:
```json
{
  ...
  "mapper": {
    "plugin": "SimpleMapper",
    "settings": {
      "username": "kolmogorov", "password_hash": "goodluckgettingthishash",
      "resources": [
        {
          "name": "Elisabeth Taylor",
          "hostname": "vmwr-test-01.example.com"
        },
        {
          "name": "James Dean",
          "hostname": "vmwr-test-01.example.com"
        },
        {
          "name": "Marlon Brando",
          "hostname": "localhost"
        }
      ],
      "domains": ["example.com"]
    }
  }
}
```

#### Generating a password hash
The username and password is stored in the settings. To provide a modicum of security over a plaintext password, we require
the password to be "pre-hashed". That way we won't store a plaintext password anywhere.

To generate a hashed password, simply call:

```shell script
python -m interstate_love_song.mapping.simple "a very long password"
```

### Plugin Mappers

Mappers can be written as plugins in separate python packages.  
To be able to find your plugin, you need to define an entrypoint in your `setup.py`:

```
setup(
  ...
  entry_points={'interstate_love_song.plugins': 'SimpleWebserviceMapper = SimpleWebserviceMapper'},
  ...
)
```

For an example, check out our [SimpleWebServiceMapper repo](https://github.com/ilpvfx/interstate_love_song.SimpleWebserviceMapper).


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

If you want to run Gunicorn, you need gunicorn and possibly dependencies needed by the worker class. For example, 
"gevent", naturally requires "gevent".

If you want to use the CherryPy's runner or Werkzeug, you'll need those packages as well.

## Formatting and Linting

We are using [black](https://github.com/psf/black) to format the code and we allow a line length of `127` columns.  
The CI will run `python -m black --check source --target-version py37 --line-length 127` to fail if the code is not properly formatted.  
To test locally you can install black with `pip install black==19.10b0`  
It is highly recommended to configure your IDE to run formatting on save with these settings.
