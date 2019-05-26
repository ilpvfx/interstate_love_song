# :coding: utf-8
# :copyright: Copyright (c) 2019 ilp

import json
import falcon
import logging


logger = logging.getLogger(__name__)


def set_allowed_headers(rq, resp, resource):
    resp.set_header("Allow", "POST")


@falcon.after(set_allowed_headers)
class BaseResource(object):
    def __init__(self):
        self.logger = logging.getLogger("{0}.{1}".format(__name__, self.__class__.__name__))

    def _set_error(self, resp, status, message, exception=None):
        resp.status = status

        resp.body = json.dumps({"error": message})

        logger.error(message)

        if exception is not None:
            logger.exception(exception)

        return None
