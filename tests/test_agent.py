import pytest
import httpretty
from xmldiff.main import diff_texts

from interstate_love_song.agent import allocate_session, AllocateSessionStatus


@httpretty.activate
def test_allocate_session_host_unreachable():
    status, result = allocate_session(123, "127.255.255.255", username="Paul", password="Dirac")
    assert result is None
    assert status == AllocateSessionStatus.CONNECTION_ERROR


@httpretty.activate
def test_allocate_session_host_404():
    httpretty.register_uri(
        httpretty.POST,
        "https://euler.edu:60443/pcoip-agent/xml",
        body="Not found, my man!",
        status=404,
    )

    status, result = allocate_session(123, "euler.edu", username="Paul", password="Dirac")
    assert result is None
    assert status == AllocateSessionStatus.ENDPOINT_ERROR


@httpretty.activate
def test_allocate_session():
    httpretty.register_uri(
        httpretty.POST,
        "https://euler.edu:60443/pcoip-agent/xml",
        status=200,
        body="""<?xml version="1.0"?>
        <pcoip-agent version="1.0">
            <launch-session-resp>
                <result-id>SUCCESSFUL</result-id>
                <session-info>
                    <ip-address>1.1.1.1</ip-address>
                    <sni>SNI</sni>
                    <port>60443</port>
                    <session-id>1234</session-id>
                    <session-tag>abcd</session-tag>
                </session-info>
            </launch-session-resp>
        </pcoip-agent>
        """,
    )

    status, result = allocate_session(
        123,
        "euler.edu",
        username="Paul",
        password="Dirac",
        client_name="WOPR",
        domain="bourbaki.org",
    )

    assert status == AllocateSessionStatus.SUCCESSFUL

    assert result.ip_address == "1.1.1.1"
    assert result.sni == "SNI"
    assert result.port == 60443
    assert result.session_id == "1234"
    assert result.session_tag == "abcd"
    assert result.resource_id == "123"

    req = httpretty.last_request()

    expected_req = """<pcoip-agent version="1.0">
      <launch-session>
        <session-type>UNSPECIFIED</session-type>
        <ip-address>127.0.0.1</ip-address>
        <hostname>euler.edu</hostname>
        <logon method="windows-password">
          <username>Paul</username>
          <password>Dirac</password>
          <domain>bourbaki.org</domain>
        </logon>
        <client-mac></client-mac>
        <client-ip></client-ip>
        <client-name>WOPR</client-name>
        <license-path></license-path>
        <session-log-id></session-log-id>
      </launch-session>
    </pcoip-agent>
    """

    assert len(diff_texts(expected_req, req.body)) == 0


@httpretty.activate
def test_allocate_session_user_auth_fail():
    httpretty.register_uri(
        httpretty.POST,
        "https://euler.edu:60443/pcoip-agent/xml",
        status=200,
        body="""<?xml version="1.0"?>
        <pcoip-agent version="1.0">
          <launch-session-resp>
            <result-id>FAILED_USER_AUTH</result-id>
            <fail-reason>Failed to start the session due to user authentication failing.</fail-reason>
          </launch-session-resp>
        </pcoip-agent>""",
    )

    status, result = allocate_session(
        123,
        "euler.edu",
        username="Paul",
        password="Dirac",
        client_name="WOPR",
        domain="bourbaki.org",
    )

    assert status == AllocateSessionStatus.FAILED_USER_AUTH


@httpretty.activate
def test_allocate_session_already_in_use():
    httpretty.register_uri(
        httpretty.POST,
        "https://euler.edu:60443/pcoip-agent/xml",
        status=200,
        body="""<?xml version="1.0"?>
            <pcoip-agent version="1.0">
            <launch-session-resp>
                <result-id>FAILED_ANOTHER_SESSION_STARTED</result-id>
                <fail-reason>Failed to start the session due to there being an existing session for a different user.</fail-reason>
              </launch-session-resp>
            </pcoip-agent>""",
    )

    status, result = allocate_session(
        123,
        "euler.edu",
        username="Paul",
        password="Dirac",
        client_name="WOPR",
        domain="bourbaki.org",
    )

    assert status == AllocateSessionStatus.FAILED_ANOTHER_SESION_STARTED
