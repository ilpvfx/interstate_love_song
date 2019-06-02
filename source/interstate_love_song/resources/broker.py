import falcon
import dicttoxml
import collections

from xml.etree import ElementTree

from .base import BaseResource


class BrokerResource(BaseResource):
    def elementtree_to_dict(self, element):
        node = collections.OrderedDict()

        node.update(element.items())

        child_nodes = {}
        for child in element:
            child_nodes.setdefault(child.tag, []).append(self.elementtree_to_dict(child))

        for key, value in child_nodes.items():
            if len(value) == 1:
                child_nodes[key] = value[0]

        if element.text:
            node["_value"] = element.text

        node.update(child_nodes.items())

        return node

    def get_session(self, req):
        if "beaker.session" in req.env:
            """We might not have a session since we 
            can not get the pcoip client to store the cookie..?"""
            return req.env["beaker.session"]

        return {}

    def on_post(self, req, resp):

        if req.content_type and "text/xml" in req.content_type:

            if req.content_length is (None, 0):
                return self._set_error(resp, falcon.HTTP_400, "POST body sent invalid XML")

            raw_input_data = req.stream.read()

            try:
                data = self.elementtree_to_dict(
                    ElementTree.fromstring(raw_input_data.decode("utf-8"))
                )

            except ValueError as error:
                return self._set_error(resp, falcon.HTTP_400, str(error), error)

            except Exception as error:
                return self._set_error(resp, falcon.HTTP_400, str(error), error)

            return self.handle_request(req, resp, data)

    def handle_request(self, req, resp, data):
        if "version" not in data:
            return self._set_error(resp, falcon.HTTP_400, "Invalid request, missing version.")

        _version = data.pop("version")

        _session = self.get_session(req)

        from interstate_love_song.resources.messages import base

        response_cls = None

        for key in data:
            if key in ("hello",):
                response_cls = base.HelloResponse

            elif key in ("authenticate",):
                response_cls = base.AuthenticateResponse

            elif key in ("get-resource-list",):
                response_cls = base.GetResourceListResponse

            elif key in ("allocate-resource",):
                response_cls = base.AllcateResourceResponse

        if response_cls:
            resp.stream = [response_cls(data, _session)._serialize().encode("UTF-8")]
