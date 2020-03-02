from io import BytesIO

import pytest

from interstate_love_song.serialization import serialize_message, deserialize_message
from interstate_love_song.transport import *

from defusedxml.ElementTree import tostring, fromstring
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


def test_serialize_message_authenticate_success_response():
    msg = AuthenticateSuccessResponse()

    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <authenticate-resp method="password">
            <result>
                <result-id>AUTH_SUCCESSFUL_AND_COMPLETE</result-id>
                <result-str>Authentication was a resounding success.</result-str>
            </result>
        </authenticate-resp>
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_serialize_message_authenticate_failed_response():
    msg = AuthenticateFailedResponse()

    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <authenticate-resp method="password">
            <result>
                <result-id>AUTH_FAILED_UNKNOWN_USERNAME_OR_PASSWORD</result-id>
                <result-str>Could not authenticate.</result-str>
            </result>
        </authenticate-resp>
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_serialize_message_get_resource_list_response():
    resource = TeradiciResource("Euler", "Lagrange")
    msg = GetResourceListResponse([resource])

    expected = """<?xml version="1.0"?>
        <pcoip-client version="2.1">
            <get-resource-list-resp>
                <result>
                    <result-id>LIST_SUCCESSFUL</result-id>
                    <result-str>Khajit has wares.</result-str>
                </result>
                <resource>
                    <resource-name>{msg.resources[0].resource_name}</resource-name>
                    <resource-id>{msg.resources[0].resource_id}</resource-id>
                    <resource-type session-type="{msg.resources[0].session_type}">{msg.resources[0].resource_type}</resource-type>
                    <resource-state>{msg.resources[0].resource_state}</resource-state>
                    <protocols>
                        <protocol is-default="true">{msg.resources[0].protocol}</protocol>
                    </protocols>
                </resource>
            </get-resource-list-resp>
        </pcoip-client>
        """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_serialize_message_allocate_resource_success_response():
    msg = AllocateResourceSuccessResponse(
        "euler", "euler.gov", "lagrange", 666, "1234", "1234", 999
    )
    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <allocate-resource-resp>
            <result>
                <result-id>ALLOC_SUCCESSFUL</result-id>
                <result-str>The Spice must flow</result-str>
            </result>
            <target>
                <ip-address>{msg.ip_address}</ip-address>
                <hostname>{msg.hostname}</hostname>
                <sni>{msg.sni}</sni>
                <port>{msg.port}</port>
                <session-id>{msg.session_id}</session-id>
                <connect-tag>{msg.connect_tag}</connect-tag>
            </target>
            <resource-id>{msg.resource_id}</resource-id>
            <protocol>{msg.protocol}</protocol>
        </allocate-resource-resp>
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_serialize_message_allocate_resource_failure_response():
    msg = AllocateResourceFailureResponse(result_id="XENOMORPHS_RUNNING_LOSE")
    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <allocate-resource-resp>
            <result>
                <result-id>{msg.result_id}</result-id>
                <result-str>Failed to allocate a session on the given resource 😢.</result-str>
            </result>
        </allocate-resource-resp>
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_serialize_message_bye_response():
    msg = ByeResponse()
    expected = """<?xml version="1.0"?>
    <pcoip-client version="2.1">
        <bye-resp />
    </pcoip-client>
    """.format(
        msg=msg
    )

    xml_et = serialize_message(msg)

    assert xml_tree_equal_to_xml_string(xml_et, expected)


def test_deserialize_message_bad_input():
    with pytest.raises(ValueError):
        deserialize_message(123)


def test_deserialize_message_missing_version():
    xml = """<?xml version="1.0"?>
    <pcoip-client>
      <hello>
        <client-info>
          <product-name>QueryBrokerClient</product-name>
          <product-version>1.0</product-version>
          <platform>PCoIP</platform>
          <locale>en_US</locale>
          <hostname>euler.leonhard.gov</hostname>
          <serial-number>00:00:00:00:00:00</serial-number>
          <device-name>euler.leonhard.gov</device-name>
          <pcoip-unique-id>00:00:00:00:00:00</pcoip-unique-id>
        </client-info>
      </hello>
    </pcoip-client>
    """

    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, BadMessage)


def test_deserialize_message_hello():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <hello>
        <client-info>
          <product-name>Teradici PCoIP Desktop Client</product-name>
          <product-version>19.11.0</product-version>
          <platform>CentOS Linux 7 (Core) linux 3.10.0-862.9.1.el7.x86_64 x86_64</platform>
          <locale>en_US</locale>
          <hostname>euler.leonhard.gov</hostname>
          <serial-number>00:00:00:00:00:00</serial-number>
          <device-name>euler.leonhard.gov</device-name>
          <pcoip-unique-id>00:00:00:00:00:00</pcoip-unique-id>
        </client-info>
        <caps>
          <cap>CAP_DISCLAIMER_AUTHENTICATION</cap>
          <cap>CAP_NO_AUTHENTICATION</cap>
          <cap>CAP_DIALOG_AUTHENTICATION</cap>
          <cap>CAP_ALTERNATE_PROVISIONING</cap>
        </caps>
        <server-address>
          <ip-address>::1</ip-address>
          <hostname>ignore.edu</hostname>
        </server-address>
      </hello>
    </pcoip-client>
    """

    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, HelloRequest)
    assert msg.client_hostname == "euler.leonhard.gov"
    assert msg.client_product_name == "Teradici PCoIP Desktop Client"


def test_deserialize_message_authenticate():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <authenticate method="password">
        <username>dtrump</username>
        <password>ilovemyself</password>
        <domain></domain>
      </authenticate>
    </pcoip-client>
    """

    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, AuthenticateRequest)
    assert msg.username == "dtrump"
    assert msg.password == "ilovemyself"


def test_deserialize_message_get_resource_list():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <get-resource-list>
        <protocols>
          <protocol>PCOIP</protocol>
        </protocols>
        <resource-types>
          <resource-type>DESKTOP</resource-type>
        </resource-types>
      </get-resource-list>
    </pcoip-client>
    """
    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, GetResourceListRequest)


def test_deserialize_message_allocate_resource():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <allocate-resource>
        <resource-id>666</resource-id>
        <protocol>PCOIP</protocol>
        <client-info>
          <ip-address>::1</ip-address>
          <mac-address>00:00:00:00:00:00</mac-address>
        </client-info>
      </allocate-resource>
    </pcoip-client>
    """
    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, AllocateResourceRequest)
    assert msg.resource_id == 666


def test_deserialize_message_allocate_resource_not_integer():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <allocate-resource>
        <resource-id>Not an integer</resource-id>
        <protocol>PCOIP</protocol>
        <client-info>
          <ip-address>::1</ip-address>
          <mac-address>00:00:00:00:00:00</mac-address>
        </client-info>
      </allocate-resource>
    </pcoip-client>
    """
    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, BadMessage)


def test_deserialize_message_bye():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <pcoip-client version="2.1">
      <bye/>
    </pcoip-client>
    """
    msg = deserialize_message(fromstring(xml))

    assert isinstance(msg, ByeRequest)
