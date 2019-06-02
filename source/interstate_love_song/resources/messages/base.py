from io import BytesIO

from xml.etree import ElementTree


class BaseResponse(object):
    def __init__(self, data, session):
        self.data, self.session = (data, session)

    def serialize(self, parent):
        return parent

    def _serialize(self):
        base = ElementTree.Element("pcoip-client", version="2.1")

        node = self.serialize(base)

        et = ElementTree.ElementTree(base)

        f = BytesIO()

        et.write(f, encoding="UTF-8", xml_declaration=True)

        return f.getvalue().decode("UTF-8")


class HelloResponse(BaseResponse):
    def get_brokers(self):
        return [1]

    def get_authentication_methods(self):
        return ("AUTHENTICATE_VIA_PASSWORD",)

    def get_domains(self):
        return ("example.com",)

    def get_brokers_info(self, parent):
        response = ElementTree.SubElement(parent, "brokers-info")

        for broker in self.get_brokers():
            broker_element = ElementTree.SubElement(response, "broker-info")
            for key, value in (
                ("product-name", "interstate love song"),
                ("product-version", "0.0.1"),
                ("platform", "linux"),
                ("locale", "en_US"),
                ("ip-address", "CHANGE_ME"),
                ("hostname", "potatis.example.com"),
            ):

                ElementTree.SubElement(broker_element, key).text = value

    def get_next_authentication(self, parent):
        response = ElementTree.SubElement(parent, "next-authentication")

        methods = ElementTree.SubElement(response, "authentication-methods")

        for method in self.get_authentication_methods():
            ElementTree.SubElement(methods, "method").text = method

        domains = ElementTree.SubElement(response, "domains")

        for domain in self.get_domains():
            ElementTree.SubElement(domains, "domain").text = domain

    def serialize(self, parent):
        response = ElementTree.SubElement(parent, "hello-resp")

        self.get_brokers_info(response)

        self.get_next_authentication(response)

        return response


class AuthenticateResponse(BaseResponse):
    def serialize(self, parent):

        print("GET THE DATA", self.session, self.data)

        self.session["user"], self.session["password"] = (
            self.data["authenticate"]["username"],
            self.data["authenticate"]["password"],
        )
        response = ElementTree.SubElement(parent, "authenticate-resp", method="password")

        result = ElementTree.SubElement(response, "result")

        ElementTree.SubElement(result, "result-id").text = "AUTH_SUCCESSFUL_AND_COMPLETE"

        ElementTree.SubElement(result, "result-str").text = "Authentication completed successfully"

        return response


class GetResourceListResponse(BaseResponse):
    def get_resources(self):
        return [1, 2]

    def serialize(self, parent):
        response = ElementTree.SubElement(parent, "get-resource-list-resp")

        result = ElementTree.SubElement(response, "result")

        ElementTree.SubElement(result, "result-id").text = "LIST_SUCCESSFUL"

        ElementTree.SubElement(result, "result-str").text = "The user is entitled to resources"

        for resource_ in self.get_resources():
            resource = ElementTree.SubElement(response, "resource")

            for key, value in (
                ("resource-name", "test" + str(resource_)),
                ("resource-id", "abcdef9876543210" + str(resource_)),
            ):
                ElementTree.SubElement(resource, key).text = value

            ElementTree.SubElement(
                resource, "resource-type", **{"session-type": "VDI"}
            ).text = "DESKTOP"

            ElementTree.SubElement(resource, "resource-state",).text = "UNKNOWN"

            protocols = ElementTree.SubElement(resource, "protocols")

            ElementTree.SubElement(protocols, "protocol", **{"is-default": "true"}).text = "PCOIP"

        return response


class AllcateResourceResponse(BaseResponse):
    def get_target(self):
        return [1]

    def serialize(self, parent):
        response = ElementTree.SubElement(parent, "allocate-resource-resp")

        result = ElementTree.SubElement(response, "result")

        ElementTree.SubElement(result, "result-id").text = "ALLOC_SUCCESSFUL"

        ElementTree.SubElement(result, "result-str").text = "Successfully allocated resource"

        import requests

        result = requests.post(
            "https://jh-sys.example.com:60443/pcoip-agent/xml",
            data="""
            <?xml version='1.0' encoding='UTF-8'?>
            <pcoip-agent version="1.0">
              <launch-session>
                <session-type>UNSPECIFIED</session-type>
                <ip-address>172.16.43.3</ip-address>
                <hostname>jh-sys.example.com</hostname>
                <logon method="windows-password">
                  <username>erhe</username>
                  <password>xxx</password>
                  <domain>example.com</domain>
                </logon>
                <client-mac>28:b2:bd:ed:a4:7c</client-mac>
                <client-ip>10.27.0.5</client-ip>
                <client-name>ford</client-name>
                <license-path>2589@license-server-ip-address-or-host-name</license-path>
                <session-log-id>d9836980-34c4-1fed-9dea-000000000000</session-log-id>
              </launch-session>
            </pcoip-agent>

            """,
            verify=False,
        )

        from interstate_love_song import util

        data = util.elementtree_to_dict(ElementTree.fromstring(result.text))

        session_info = data["launch-session-resp"].get("session-info")

        for resource in self.get_target():
            resource = ElementTree.SubElement(response, "target")

            for key, value in (
                ("ip-address", session_info.get("ip-address").get("_value")),
                ("hostname", session_info.get("sni").get("_value")),
                ("sni", session_info.get("sni").get("_value")),
                ("port", session_info.get("port").get("_value")),
                ("session-id", session_info.get("session-id").get("_value")),
                ("connect-tag", session_info.get("session-tag").get("_value")),
            ):
                ElementTree.SubElement(resource, key).text = value

        ElementTree.SubElement(response, "resource-id",).text = "abcdef98765432101"

        ElementTree.SubElement(response, "protocol",).text = "PCOIP"

        return response
