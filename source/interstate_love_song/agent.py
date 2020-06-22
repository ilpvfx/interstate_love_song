import logging
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import Optional, Tuple
from xml.etree.ElementTree import Element, SubElement, ElementTree, fromstring

import requests
from urllib3.exceptions import NewConnectionError

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0


class AllocateSessionStatus(Enum):
    # Protocol status
    SUCCESSFUL = 0
    FAILED_USER_AUTH = 1
    FAILED_ANOTHER_SESSION_STARTED = 2
    # Library status
    CONNECTION_ERROR = 100
    XML_ERROR = 101
    ENDPOINT_ERROR = 102


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
    domain: str,
    client_name: str = "Bobby McGee",
    session_type: str = "UNSPECIFIED",
    timeout=REQUEST_TIMEOUT,
) -> Tuple[AllocateSessionStatus, Optional[AgentSession]]:
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

    def parse_xml_response(
        response_xml: Element,
    ) -> Tuple[AllocateSessionStatus, Optional[AgentSession]]:
        result_id = response_xml.find("launch-session-resp/result-id")
        if result_id is None:
            return AllocateSessionStatus.XML_ERROR, None

        if result_id.text.lower() == "successful":
            session_info = response_xml.find("launch-session-resp/session-info")
            if session_info is None:
                return AllocateSessionStatus.XML_ERROR, None

            session_properties = {"resource_id": str(resource_id)}
            for property in ("ip-address", "sni", "port", "session-id", "session-tag"):
                element = session_info.find(property)
                if element is None:
                    return AllocateSessionStatus.XML_ERROR, None

                session_properties[property.replace("-", "_")] = (
                    element.text if property != "port" else int(element.text)
                )

            return AllocateSessionStatus.SUCCESSFUL, AgentSession(**session_properties)
        elif result_id.text.lower() == "failed_user_auth":
            return AllocateSessionStatus.FAILED_USER_AUTH, None
        elif result_id.text.lower() == "failed_another_session_started":
            return AllocateSessionStatus.FAILED_ANOTHER_SESSION_STARTED, None
        else:
            logger.warning("Unknown result-id: %s", result_id.text)
            return AllocateSessionStatus.XML_ERROR, None

    try:
        response = requests.post(
            "https://{}:60443/pcoip-agent/xml".format(agent_hostname),
            data=request_body.getvalue().decode("utf-8"),
            verify=False,
            timeout=timeout,
        )

        if response.status_code != 200:
            return AllocateSessionStatus.ENDPOINT_ERROR, None
        response_xml = fromstring(response.text)

        status, agent_session = parse_xml_response(response_xml)
        if not agent_session:
            logger.info("Failure when deconstructing XML from agent at {}.".format(agent_hostname))
        return status, agent_session

    except SyntaxError as se:
        logger.info("Could not parse XML returned from Agent: {}".format(se))
        return AllocateSessionStatus.XML_ERROR, None
    except requests.exceptions.ConnectionError as ce:
        logger.info(
            "Could not establish a connection to the agent host {}: {}".format(agent_hostname, ce)
        )
        return AllocateSessionStatus.CONNECTION_ERROR, None
    except NewConnectionError as nce:
        logger.info("Could not establish a connection to the agent host {}.".format(agent_hostname))
        return AllocateSessionStatus.CONNECTION_ERROR, None
