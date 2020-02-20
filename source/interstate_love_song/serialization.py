from typing import Any

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

    if msg_type is HelloResponse:
        return _serialize_hello_response(msg)
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