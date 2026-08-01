import base64
import hashlib
import os
import struct
import unittest
from unittest.mock import patch

import server


class TerminalTest(unittest.TestCase):
    def test_accept_key_matches_rfc_example(self):
        self.assertEqual(
            server._ws_accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_accept_key_deterministic(self):
        self.assertEqual(
            server._ws_accept_key("abc"),
            server._ws_accept_key("abc"),
        )

    def test_terminal_enabled_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(server.terminal_enabled())

    def test_terminal_disabled(self):
        with patch.dict(os.environ, {"IDM_TERMINAL": "0"}, clear=True):
            self.assertFalse(server.terminal_enabled())

    def test_encode_frame_small(self):
        frame = server._ws_encode_frame(b"hello", opcode=0x1)
        self.assertEqual(frame[0], 0x81)
        self.assertEqual(frame[1], 5)
        self.assertEqual(frame[2:], b"hello")

    def test_encode_frame_medium_len(self):
        payload = b"x" * 300
        frame = server._ws_encode_frame(payload, opcode=0x1)
        self.assertEqual(frame[0], 0x81)
        self.assertEqual(frame[1], 126)
        self.assertEqual(struct.unpack(">H", frame[2:4])[0], 300)

    def test_encode_frame_close_opcode(self):
        frame = server._ws_encode_frame(b"", opcode=0x8)
        self.assertEqual(frame[0], 0x88)
        self.assertEqual(frame[1], 0)

    def test_decode_frame_masked_text(self):
        import socket

        payload = b"echo hi"
        mask = b"\x11\x22\x33\x44"
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        raw = bytes([0x81, 0x80 | len(payload)]) + mask + masked

        server_sock, client_sock = socket.socketpair()
        try:
            client_sock.sendall(raw)
            frame = server._ws_decode_frame(server_sock)
            self.assertEqual(frame["opcode"], 0x1)
            self.assertEqual(frame["payload"], b"echo hi")
        finally:
            server_sock.close()
            client_sock.close()

    def test_decode_frame_16bit_length(self):
        import socket

        payload = b"y" * 300
        mask = b"\x01\x02\x03\x04"
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        raw = (
            bytes([0x81, 0x80 | 126])
            + struct.pack(">H", 300)
            + mask
            + masked
        )

        server_sock, client_sock = socket.socketpair()
        try:
            client_sock.sendall(raw)
            frame = server._ws_decode_frame(server_sock)
            self.assertEqual(frame["opcode"], 0x1)
            self.assertEqual(frame["payload"], payload)
        finally:
            server_sock.close()
            client_sock.close()

    def test_decode_frame_close(self):
        import socket

        server_sock, client_sock = socket.socketpair()
        try:
            client_sock.sendall(bytes([0x88, 0x00]))
            frame = server._ws_decode_frame(server_sock)
            self.assertEqual(frame["opcode"], 0x8)
        finally:
            server_sock.close()
            client_sock.close()


if __name__ == "__main__":
    unittest.main()
