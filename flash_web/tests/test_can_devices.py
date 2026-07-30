import unittest
from unittest.mock import patch

import server


class CanDevicesTest(unittest.TestCase):
    @patch("server.detect_environment", return_value={"can_interface": "can0"})
    @patch("server.moonraker_request")
    def test_merges_unassigned_and_configured_mcus(self, moonraker_request, _):
        def response(endpoint):
            if endpoint.startswith("/machine/peripherals/canbus"):
                return {"result": {"can_uuids": [{
                    "uuid": "AABBCCDDEEFF", "application": "Katapult",
                }]}}
            if endpoint == "/printer/objects/query?configfile":
                return {"result": {"status": {"configfile": {"settings": {
                    "mcu toolhead": {"canbus_uuid": "112233445566"},
                }}}}}
            if endpoint == "/printer/objects/list":
                return {"result": {"objects": ["mcu", "mcu toolhead"]}}
            return {"result": {"status": {"mcu toolhead": {
                "mcu_constants": {"MCU": "STM32F072"},
                "mcu_version": "v0.12.0",
            }}}}

        moonraker_request.side_effect = response

        result = server.query_can_devices()

        self.assertEqual(result["katapult_uuids"], ["aabbccddeeff"])
        self.assertEqual(result["klipper_uuids"], ["112233445566"])
        toolhead = next(device for device in result["can_devices"] if device["name"] == "toolhead")
        self.assertEqual(toolhead["mcu_model"], "STM32F072")
        self.assertEqual(toolhead["source"], "runtime")


if __name__ == "__main__":
    unittest.main()
