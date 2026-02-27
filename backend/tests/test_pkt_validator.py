import pytest
import xml.etree.ElementTree as ET

from app.services.pkt_generator.validator import (
    validate_pkt_xml,
    MissingSaveRefIdError,
    OrphanLinkEndpointError,
)


def _xml(text: str) -> ET.Element:
    return ET.fromstring(text)


def test_validate_pkt_xml_ok():
    root = _xml(
        """
        <PACKETTRACER5>
          <NETWORK>
            <DEVICES>
              <DEVICE>
                <ENGINE>
                  <NAME>R1</NAME>
                  <SAVE_REF_ID>save-ref-id:111</SAVE_REF_ID>
                  <SAVEREFID>save-ref-id:111</SAVEREFID>
                </ENGINE>
              </DEVICE>
              <DEVICE>
                <ENGINE>
                  <NAME>PC0</NAME>
                  <SAVE_REF_ID>save-ref-id:222</SAVE_REF_ID>
                  <SAVEREFID>save-ref-id:222</SAVEREFID>
                </ENGINE>
              </DEVICE>
            </DEVICES>
            <LINKS>
              <LINK>
                <CABLE>
                  <FROM>save-ref-id:111</FROM>
                  <TO>save-ref-id:222</TO>
                  <PORT>FastEthernet0/0</PORT>
                  <PORT>FastEthernet0</PORT>
                </CABLE>
              </LINK>
            </LINKS>
          </NETWORK>
        </PACKETTRACER5>
        """
    )

    validate_pkt_xml(root)  # should not raise


def test_validate_pkt_xml_missing_ref():
    root = _xml(
        """
        <PACKETTRACER5>
          <NETWORK>
            <DEVICES>
              <DEVICE>
                <ENGINE>
                  <NAME>R1</NAME>
                  <SAVE_REF_ID>save-ref-id:111</SAVE_REF_ID>
                </ENGINE>
              </DEVICE>
            </DEVICES>
            <LINKS>
              <LINK>
                <CABLE>
                  <FROM>save-ref-id:111</FROM>
                  <TO>save-ref-id:999</TO>
                </CABLE>
              </LINK>
            </LINKS>
          </NETWORK>
        </PACKETTRACER5>
        """
    )

    with pytest.raises(OrphanLinkEndpointError):
        validate_pkt_xml(root)


def test_validate_pkt_xml_no_saveref_tags():
    root = _xml(
        """
        <PACKETTRACER5>
          <NETWORK>
            <DEVICES></DEVICES>
            <LINKS></LINKS>
          </NETWORK>
        </PACKETTRACER5>
        """
    )

    with pytest.raises(MissingSaveRefIdError):
        validate_pkt_xml(root)
