from typing import Any, Optional

from .transport import *

from defusedxml.ElementTree import fromstring as xml_fromstring
from xml.etree.ElementTree import ElementTree, Element, SubElement


class UnsupportedMessage(Exception):
    pass


def serialize_message(msg: Message) -> Element:
    """Serializes a message to XML. Only serializes *Response messages.

    :raises ValueError:
        msg is not an instance of Message.
    :raises UnsupportedMessage:
        msg is not of a type supported for serialization.
    :returns: A ElementTree representation of the XML.
    """
    if not isinstance(msg, Message):
        raise ValueError("msg must be an instance of Message.")

    msg_type = type(msg)

    routing_table = {
        HelloResponse: _serialize_hello_response,
        AuthenticateSuccessResponse: _serialize_authenticate_response,
        AuthenticateFailedResponse: _serialize_authenticate_failed_response,
        GetResourceListResponse: _serialize_get_resource_list_response,
        AllocateResourceSuccessResponse: _serialize_allocate_resource_success_response,
        AllocateResourceFailureResponse: _serialize_allocate_resource_failure_response,
        ByeResponse: _serialize_bye_response,
    }

    if msg_type in routing_table:
        return routing_table[msg_type](msg)
    else:
        raise UnsupportedMessage()


def _get_common_root() -> Element:
    return Element("pcoip-client", version="2.1")


def _serialize_hello_response(msg: HelloResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "hello-resp")

    brokers_info = SubElement(resp, "brokers-info")
    broker_info = SubElement(brokers_info, "broker-info")
    SubElement(broker_info, "product-name").text = msg.product_name
    SubElement(broker_info, "product-version").text = msg.product_version
    SubElement(broker_info, "platform").text = msg.platform
    SubElement(broker_info, "locale").text = msg.locale
    SubElement(broker_info, "ip-address").text = msg.ip_address
    SubElement(broker_info, "hostname").text = msg.hostname

    next_authentication = SubElement(resp, "next-authentication")

    authentication_methods = SubElement(next_authentication, "authentication-methods")
    for method in msg.authentication_methods:
        SubElement(authentication_methods, "method").text = method

    domains = SubElement(next_authentication, "domains")
    for domain in msg.domains:
        SubElement(domains, "domain").text = domain

    return root


def _serialize_authenticate_response(msg: AuthenticateSuccessResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "authenticate-resp", method="password")

    result = SubElement(resp, "result")

    SubElement(result, "result-id").text = "AUTH_SUCCESSFUL_AND_COMPLETE"
    SubElement(result, "result-str").text = "Authentication was a resounding success."

    return root


def _serialize_authenticate_failed_response(msg: AuthenticateFailedResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "authenticate-resp", method="password")

    result = SubElement(resp, "result")

    SubElement(result, "result-id").text = "AUTH_FAILED_UNKNOWN_USERNAME_OR_PASSWORD"
    SubElement(result, "result-str").text = "Could not authenticate."

    return root


def _serialize_get_resource_list_response(msg: GetResourceListResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "get-resource-list-resp")

    result = SubElement(resp, "result")

    SubElement(result, "result-id").text = "LIST_SUCCESSFUL"
    SubElement(result, "result-str").text = "Khajit has wares."

    for resource in msg.resources:
        r = SubElement(resp, "resource")

        SubElement(r, "resource-name").text = resource.resource_name
        SubElement(r, "resource-id").text = resource.resource_id
        SubElement(
            r, "resource-type", {"session-type": resource.session_type}
        ).text = resource.resource_type
        SubElement(r, "resource-state").text = resource.resource_state

        protocols = SubElement(r, "protocols")
        SubElement(protocols, "protocol", {"is-default": "true"}).text = resource.protocol

    return root


def _serialize_allocate_resource_success_response(msg: AllocateResourceSuccessResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "allocate-resource-resp")

    result = SubElement(resp, "result")

    SubElement(result, "result-id").text = "ALLOC_SUCCESSFUL"
    SubElement(result, "result-str").text = "The Spice must flow"

    target = SubElement(resp, "target")

    SubElement(target, "ip-address").text = msg.ip_address
    SubElement(target, "hostname").text = msg.hostname
    SubElement(target, "sni").text = msg.sni
    SubElement(target, "port").text = str(msg.port)
    SubElement(target, "session-id").text = msg.session_id
    SubElement(target, "connect-tag").text = msg.connect_tag

    SubElement(resp, "resource-id").text = str(msg.resource_id)
    SubElement(resp, "protocol").text = msg.protocol

    return root


def _serialize_allocate_resource_failure_response(msg: AllocateResourceFailureResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "allocate-resource-resp")

    result = SubElement(resp, "result")

    SubElement(result, "result-id").text = msg.result_id
    SubElement(result, "result-str").text = "Failed to allocate a session on the given resource 😢."

    return root


def _serialize_bye_response(msg: ByeResponse) -> Element:
    root = _get_common_root()

    resp = SubElement(root, "bye-resp")

    return root


def deserialize_message(xml: Element) -> Message:
    """Deserializes XML to a message. Only deserializes *Request messages.

    :raises ValueError:
        xml is not an instance of Element.
    :returns: The final message. May return BadMessage indicating a message it doesn't understand.
    """
    if not isinstance(xml, Element):
        raise ValueError("expected xml to be an ElementTree element.")

    if xml.tag != "pcoip-client":
        return BadMessage("root element must be pcoip-client.")

    version = _get_version(xml)
    if not version:
        return BadMessage()

    if len(xml) != 1:
        return BadMessage("expected 1 and only 1 child to pcoip-client")
    request = xml[0]

    routing_table = {
        "hello": _deserialize_hello,
        "authenticate": _deserialize_authenticate,
        "get-resource-list": _deserialize_message_get_resource_list,
        "allocate-resource": _deserialize_message_allocate_resource,
        "bye": _deserialize_bye,
    }

    if request.tag not in routing_table:
        return BadMessage()

    return routing_table[request.tag](request)


def _get_version(root: Element) -> Optional[str]:
    return root.get("version", None)


def _deserialize_hello(request_xml: Element) -> Message:
    client_info = request_xml.find("client-info")
    if client_info is None:
        return BadMessage("Could not find client-info")

    hostname = client_info.find("hostname")
    if hostname is None:
        return BadMessage("Could not find client-info/hostname")

    product_name = client_info.find("product-name")
    if product_name is None:
        return BadMessage("Could not find client-info/product-name")

    return HelloRequest(hostname.text, product_name.text)


def _deserialize_authenticate(request_xml: Element) -> Message:
    username = request_xml.find("username")
    password = request_xml.find("password")
    domain = request_xml.find("domain")

    if username is None or password is None:
        return BadMessage("Missing either username or password element.")

    return AuthenticateRequest(username.text, password.text, domain.text)


def _deserialize_message_get_resource_list(request_xml: Element) -> Message:
    return GetResourceListRequest()


def _deserialize_message_allocate_resource(request_xml: Element) -> Message:
    resource_id = request_xml.find("resource-id")
    if resource_id is None:
        return BadMessage("No resource-id element.")

    try:
        return AllocateResourceRequest(resource_id.text)
    except ValueError:
        return BadMessage("resource-id was not an integer.")


def _deserialize_bye(request_xml: Element) -> Message:
    return ByeRequest()
