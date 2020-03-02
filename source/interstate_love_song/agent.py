import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, ElementTree, fromstring

import requests
from urllib3.exceptions import NewConnectionError, ConnectTimeoutError, MaxRetryError

logger = logging.getLogger(__name__)


@dataclass
class AgentSession:
    ip_address: str
    sni: str
    port: int
    session_id: str
    session_tag: str
    resource_id: str


def allocate_session(
    resource_id: str,
    agent_hostname: str,
    username: str,
    password: str,
    domain="",
    client_name: str = "Bobby McGee",
    session_type: str = "UNSPECIFIED",
) -> Optional[AgentSession]:
    """Contacts a Teradici resource ("the agent"), and tries to acquire a session from it.

    :returns: The session on success, None on failure.
    """

    def build_launch_session_xml() -> Element:
        pcoip_agent = Element("pcoip-agent", version="1.0")

        launch_session = SubElement(pcoip_agent, "launch-session")

        for tag, text in [
            ("session-type", session_type),
            ("ip-address", "127.0.0.1"),
            ("hostname", agent_hostname),
        ]:
            SubElement(launch_session, tag).text = text

        logon = SubElement(launch_session, "logon", method="windows-password")

        SubElement(logon, "username").text = username
        SubElement(logon, "password").text = password
        SubElement(logon, "domain").text = domain

        for tag, text in [
            ("client-mac", ""),
            ("client-ip", ""),
            ("client-name", client_name),
            ("license-path", ""),
            ("session-log-id", ""),
        ]:
            SubElement(launch_session, tag).text = text

        return pcoip_agent

    request_body = BytesIO()
    et = ElementTree(build_launch_session_xml())
    et.write(request_body, encoding="utf-8", xml_declaration=True)

    def parse_xml_response(response_xml: Element) -> Optional[AgentSession]:
        session_info = response_xml.find("launch-session-resp/session-info")
        if session_info is None:
            return None

        session_properties = {"resource_id": str(resource_id)}
        for property in ("ip-address", "sni", "port", "session-id", "session-tag"):
            element = session_info.find(property)
            if element is None:
                return None

            session_properties[property.replace("-", "_")] = (
                element.text if property != "port" else int(element.text)
            )

        return AgentSession(**session_properties)

    try:
        response = requests.post(
            "https://{}:60443/pcoip-agent/xml".format(agent_hostname),
            data=request_body.getvalue().decode("utf-8"),
            verify=False,
        )

        response_xml = fromstring(response.text)

        agent_session = parse_xml_response(response_xml)
        if not agent_session:
            logger.info("Failure when deconstructing XML from agent at {}.".format(agent_hostname))
        return agent_session

    except SyntaxError as se:
        logger.info("Could not parse XML returned from Agent: {}".format(se))
        return None
    except requests.exceptions.ConnectionError as ce:
        logger.info(
            "Could not establish a connection to the agent host {}: {}".format(agent_hostname, ce)
        )
        return None
    except NewConnectionError as nce:
        logger.info("Could not establish a connection to the agent host {}.".format(agent_hostname))
        return None
