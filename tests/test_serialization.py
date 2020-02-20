from io import BytesIO

import pytest

from interstate_love_song.serialization import serialize_message
from interstate_love_song.transport import *

from defusedxml.ElementTree import tostring
from xmldiff.main import diff_texts


def xml_tree_equal_to_xml_string(et, xml_s: str) -> bool:
    xml_actual = tostring(et, encoding="unicode")
    actions = diff_texts(xml_actual, xml_s)
    if actions:
        print(actions)
    # No actions indicates that xmldiff thinks these two XML documents are equal.
    return len(actions) == 0


def test_serialize_message_bad_argument():
    with pytest.raises(ValueError):
        serialize_message(123)


def test_serialize_message_hello_response():
    msg = HelloResponse(hostname="euler.test")

    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <hello-resp>
            <brokers-info>
                <broker-info>
                    <product-name>{msg.product_name}</product-name>
                    <product-version>{msg.product_version}</product-version>
                    <platform>{msg.platform}</platform>
                    <locale>{msg.locale}</locale>
                    <ip-address>{msg.ip_address}</ip-address>
                    <hostname>{msg.hostname}</hostname>
                </broker-info>
            </brokers-info>
            <next-authentication>
                <authentication-methods>
                    <method>{msg.authentication_methods[0]}</method>
                </authentication-methods>
                <domains>
                    <domain>{msg.domains[0]}</domain>
                </domains>
            </next-authentication>
        </hello-resp>
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)
