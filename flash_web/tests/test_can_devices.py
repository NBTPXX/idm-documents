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
            return {"result": {"status": {"idm_mcu_info": {"mcus": [{
                "name": "mcu toolhead", "uuid": "112233445566",
                "application": "Klipper", "mcu_model": "STM32F072",
                "mcu_version": "v0.12.0",
            }]}}}}

        moonraker_request.side_effect = response

        result = server.query_can_devices()

        self.assertEqual(result["katapult_uuids"], ["aabbccddeeff"])
        self.assertEqual(result["klipper_uuids"], ["112233445566"])
        self.assertEqual(result["can_devices"][1]["mcu_model"], "STM32F072")
        self.assertEqual(result["can_devices"][1]["source"], "runtime")


if __name__ == "__main__":
    unittest.main()
