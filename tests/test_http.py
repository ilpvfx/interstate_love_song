from argparse import Namespace
from typing import Optional
from xml.etree.ElementTree import Element, tostring

import falcon
import pytest
from falcon import API
from falcon.testing import TestClient

from interstate_love_song.protocol import BrokerProtocolHandler, ProtocolState, ProtocolSession
from interstate_love_song.http import BrokerResource, get_falcon_api, SessionSetter
from interstate_love_song.transport import HelloResponse, HelloRequest
from .test_protocol import DummyMapper


def test_broker_resource_constructor():
    with pytest.raises(ValueError):
        BrokerResource(123)
    with pytest.raises(ValueError):
        BrokerResource(lambda: BrokerProtocolHandler(), serialize=123)
    with pytest.raises(ValueError):
        BrokerResource(lambda: BrokerProtocolHandler(), deserialize=123)


class DummySessionSetter(SessionSetter):
    def __init__(self):
        self.data = None

    def set_data(self, data: Optional[ProtocolSession]):
        self.data = data

    def get_data(self):
        return self.data


def test_broker_resource_on_post_bad_xml():
    api = get_falcon_api(BrokerResource(lambda: BrokerProtocolHandler(DummyMapper())))
    client = TestClient(api)

    resp = client.simulate_post("/pcoip-broker/xml", body="Not XML")

    assert resp.status == falcon.HTTP_BAD_REQUEST


def test_broker_resource_on_post_sets_session():
    def dummy_protocol(msg, data):
        return (
            ProtocolSession("leonhard", "euler", state=ProtocolState.WAITING_FOR_HELLO),
            HelloResponse("lagrange"),
        )

    session_setter = DummySessionSetter()

    api = get_falcon_api(
        BrokerResource(
            protocol_creator=lambda: dummy_protocol, session_setter_creator=lambda x: session_setter
        )
    )
    client = TestClient(api)

    resp = client.simulate_post("/pcoip-broker/xml", body="<hello/>")

    assert session_setter.data is not None
    assert session_setter.data.username == "leonhard"
    assert session_setter.data.password == "euler"


def test_broker_resource_on_post_clears_session():
    def terminate_protocol(msg, data):
        return None, HelloResponse("lagrange")

    session_setter = DummySessionSetter()

    api = get_falcon_api(
        BrokerResource(
            protocol_creator=lambda: terminate_protocol,
            session_setter_creator=lambda x: session_setter,
        )
    )
    client = TestClient(api)

    resp = client.simulate_post("/pcoip-broker/xml", body="<hello/>")

    assert session_setter.data is None


def test_broker_resource_deserializes():
    msg = HelloRequest("euler.lagrange.edu", "Abel")

    def terminate_protocol(in_msg, data):
        assert in_msg is msg
        return None, HelloResponse("lagrange")

    check = Namespace(deserialize_called=False)

    def deserialize(xml):
        check.deserialize_called = True
        return msg

    session_setter = DummySessionSetter()

    api = get_falcon_api(
        BrokerResource(
            protocol_creator=lambda: terminate_protocol,
            deserialize=deserialize,
            session_setter_creator=lambda x: session_setter,
        )
    )
    client = TestClient(api)

    resp = client.simulate_post("/pcoip-broker/xml", body="<hello/>")

    assert check.deserialize_called is True


def test_broker_resource_serializes():
    in_msg = HelloRequest("euler.lagrange.edu", "Abel")
    out_msg = HelloResponse("lagrange")

    def terminate_protocol(ignored, data):
        return None, out_msg

    def deserialize(ignored):
        return in_msg

    xml = Element("bogus")

    check = Namespace(serialize_called=False)

    def serialize(msg):
        check.serialize_called = True
        assert msg is out_msg
        return xml

    session_setter = DummySessionSetter()

    api = get_falcon_api(
        BrokerResource(
            protocol_creator=lambda: terminate_protocol,
            deserialize=deserialize,
            serialize=serialize,
            session_setter_creator=lambda x: session_setter,
        )
    )
    client = TestClient(api)

    resp = client.simulate_post("/pcoip-broker/xml", body="<hello/>")

    assert resp.text == "<?xml version='1.0' encoding='utf-8'?>\n<bogus />"

    assert check.serialize_called is True
