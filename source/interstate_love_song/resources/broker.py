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

    def on_post(self, req, resp):
        if req.content_type and "text/xml" in req.content_type:

            if req.content_length is (None, 0):
                return self._set_error(resp, falcon.HTTP_400, "POST body sent invalid XML")

            raw_input_data = req.stream.read()

            print(raw_input_data)

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

        result = None

        from interstate_love_song.resources.messages import base

        for key in data:
            if key in ("hello",):
                result = base.HelloResponse(data)._serialize()
                pass

            elif key in ("authenticate",):
                result = base.AuthenticateResponse(data)._serialize()

            elif key in ("get-resource-list",):
                result = base.GetResourceListResponse(data)._serialize()

            elif key in ("allocate-resource",):
                result = base.AllcateResourceResponse(data)._serialize()

        if result:
            resp.set_cookie(
                "JSESSIONID", "aabbccddeeff00112233445566778899", secure=True,
            )
            resp.content_type = "application/xml; charset=UTF-8"

            print(result)

            resp.stream = result
