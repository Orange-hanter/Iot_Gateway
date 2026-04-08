#!/usr/bin/env python3
"""
Unit-тесты для нового функционала авто-определения порта в bridge-скриптах:
  - usb:SERIAL синтаксис в __init__
  - discover_arduino(usb_serial=...)
  - list_arduino_ports()
  - --list-ports / --port CLI аргументы
"""

import sys
import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/Users/dakh/Git/GatewayDemo")


def _make_port(device, description, vid=0x2341, pid=0x0043, serial_number=None):
    """Создать mock объект порта (аналог serial.tools.list_ports.ListPortInfo)."""
    p = MagicMock()
    p.device = device
    p.description = description
    p.vid = vid
    p.pid = pid
    p.serial_number = serial_number
    return p


MOCK_PORTS = [
    _make_port("/dev/cu.usbserial-1220", "Arduino Uno", serial_number="ABC123"),
    _make_port("/dev/cu.usbserial-2440", "Arduino Mega", vid=0x2A03, serial_number="DEF456"),
    _make_port("/dev/cu.Bluetooth-1",    "Bluetooth Port", vid=0x0000, serial_number=None),
]


# ---------------------------------------------------------------------------
# bridge_button_dht11
# ---------------------------------------------------------------------------

class TestButtonDHT11BridgeInit(unittest.TestCase):

    @patch("arduino.bridge_button_dht11.BUFFER_DIR")
    def _make_bridge(self, port, mock_buf):
        """Создать экземпляр моста без реальной файловой системы."""
        mock_buf.__truediv__ = MagicMock(return_value=MagicMock(mkdir=MagicMock()))
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            return ArduinoButtonDHT11Bridge(device_id="test-uuid", port=port)

    def test_plain_port_stored(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            b = ArduinoButtonDHT11Bridge("dev", port="/dev/cu.usbserial-1220")
        self.assertEqual(b.port, "/dev/cu.usbserial-1220")
        self.assertIsNone(b.usb_serial)
        self.assertTrue(b.manual_port)

    def test_usb_prefix_parsed(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            b = ArduinoButtonDHT11Bridge("dev", port="usb:ABC123")
        self.assertIsNone(b.port)
        self.assertEqual(b.usb_serial, "ABC123")
        self.assertFalse(b.manual_port)

    def test_no_port_autodetect(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            b = ArduinoButtonDHT11Bridge("dev", port=None)
        self.assertIsNone(b.port)
        self.assertIsNone(b.usb_serial)
        self.assertFalse(b.manual_port)


class TestButtonDHT11DiscoverArduino(unittest.TestCase):

    def setUp(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            self.bridge = ArduinoButtonDHT11Bridge("dev")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_autodetect_finds_first_arduino(self, _mock):
        port = self.bridge.discover_arduino()
        self.assertEqual(port, "/dev/cu.usbserial-1220")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_usb_serial_finds_correct_port(self, _mock):
        port = self.bridge.discover_arduino(usb_serial="DEF456")
        self.assertEqual(port, "/dev/cu.usbserial-2440")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_usb_serial_unknown_returns_none(self, _mock):
        port = self.bridge.discover_arduino(usb_serial="XXXXXX")
        self.assertIsNone(port)

    @patch("serial.tools.list_ports.comports", return_value=[])
    def test_no_ports_returns_none(self, _mock):
        port = self.bridge.discover_arduino()
        self.assertIsNone(port)

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_connect_with_usb_serial_resolves_port(self, _mock):
        """connect() должен автоматически разрешить usb:SERIAL в TTY."""
        with patch("pathlib.Path.mkdir"):
            from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
            b = ArduinoButtonDHT11Bridge("dev", port="usb:ABC123")
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = MagicMock()
            result = b.connect()
        self.assertTrue(result)
        self.assertEqual(b.port, "/dev/cu.usbserial-1220")


class TestButtonDHT11ListPorts(unittest.TestCase):

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_list_ports_prints_table(self, _mock):
        from arduino.bridge_button_dht11 import list_arduino_ports
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            list_arduino_ports()
            output = mock_out.getvalue()
        self.assertIn("/dev/cu.usbserial-1220", output)
        self.assertIn("ABC123", output)
        self.assertIn("usb:<USB Serial>", output)

    @patch("serial.tools.list_ports.comports", return_value=[
        _make_port("/dev/cu.Bluetooth-1", "Bluetooth Port", vid=0x0000),
    ])
    def test_list_ports_no_arduino(self, _mock):
        from arduino.bridge_button_dht11 import list_arduino_ports
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            list_arduino_ports()
        self.assertIn("No Arduino-compatible devices found", mock_out.getvalue())


# ---------------------------------------------------------------------------
# bridge (MQ2)
# ---------------------------------------------------------------------------

class TestBridgeMQ2Init(unittest.TestCase):

    def _make(self, port):
        from arduino.bridge import ArduinoBridge
        with patch("pathlib.Path.mkdir"):
            return ArduinoBridge("dev", port=port)

    def test_plain_port(self):
        b = self._make("/dev/ttyUSB0")
        self.assertEqual(b.port, "/dev/ttyUSB0")
        self.assertIsNone(b.usb_serial)

    def test_usb_prefix(self):
        b = self._make("usb:DEF456")
        self.assertIsNone(b.port)
        self.assertEqual(b.usb_serial, "DEF456")

    def test_none_port(self):
        b = self._make(None)
        self.assertIsNone(b.port)
        self.assertIsNone(b.usb_serial)


class TestBridgeMQ2Discover(unittest.TestCase):

    def setUp(self):
        from arduino.bridge import ArduinoBridge
        with patch("pathlib.Path.mkdir"):
            self.bridge = ArduinoBridge("dev")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_autodetect(self, _mock):
        port = self.bridge.discover_arduino()
        self.assertEqual(port, "/dev/cu.usbserial-1220")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_by_usb_serial(self, _mock):
        port = self.bridge.discover_arduino(usb_serial="DEF456")
        self.assertEqual(port, "/dev/cu.usbserial-2440")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_unknown_usb_serial(self, _mock):
        self.assertIsNone(self.bridge.discover_arduino(usb_serial="ZZZ"))

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_connect_usb_serial_resolves(self, _mock):
        from arduino.bridge import ArduinoBridge
        with patch("pathlib.Path.mkdir"):
            b = ArduinoBridge("dev", port="usb:DEF456")
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = MagicMock()
            result = b.connect()
        self.assertTrue(result)
        self.assertEqual(b.port, "/dev/cu.usbserial-2440")


class TestBridgeMQ2ListPorts(unittest.TestCase):

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_list_ports_output(self, _mock):
        from arduino.bridge import list_arduino_ports
        with patch("sys.stdout", new_callable=StringIO) as out:
            list_arduino_ports()
        text = out.getvalue()
        self.assertIn("DEF456", text)
        self.assertIn("usb:<USB Serial>", text)


# ---------------------------------------------------------------------------
# CLI --list-ports exits 0 without --device-id
# ---------------------------------------------------------------------------

class TestCLIListPortsExit(unittest.TestCase):

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_button_dht11_list_ports_exits(self, _mock):
        with patch("sys.argv", ["bridge_button_dht11.py", "--list-ports"]):
            from arduino import bridge_button_dht11
            with self.assertRaises(SystemExit) as ctx:
                bridge_button_dht11.main()
            self.assertEqual(ctx.exception.code, 0)

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_bridge_list_ports_exits(self, _mock):
        with patch("sys.argv", ["bridge.py", "--list-ports"]):
            from arduino import bridge
            with self.assertRaises(SystemExit) as ctx:
                bridge.main()
            self.assertEqual(ctx.exception.code, 0)


# ---------------------------------------------------------------------------
# Reconnect behaviour
# ---------------------------------------------------------------------------

class TestReconnectBehaviour(unittest.TestCase):
    """Tests for disconnect detection and reconnect logic."""

    def _make_bridge(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            return ArduinoButtonDHT11Bridge("dev")

    def test_backoff_formula(self):
        b = self._make_bridge()
        # attempt 0 → 5s, 1 → 10s, 2 → 20s, 3 → 40s, 4+ → 60s (cap)
        b._reconnect_attempts = 0; self.assertEqual(b._reconnect_backoff(), 5)
        b._reconnect_attempts = 1; self.assertEqual(b._reconnect_backoff(), 10)
        b._reconnect_attempts = 2; self.assertEqual(b._reconnect_backoff(), 20)
        b._reconnect_attempts = 3; self.assertEqual(b._reconnect_backoff(), 40)
        b._reconnect_attempts = 4; self.assertEqual(b._reconnect_backoff(), 60)
        b._reconnect_attempts = 99; self.assertEqual(b._reconnect_backoff(), 60)

    def test_on_disconnect_sets_time_and_clears_port(self):
        b = self._make_bridge()
        b.port = "/dev/cu.test"
        b.serial_connection = MagicMock()
        b._on_disconnect("test reason")
        self.assertIsNotNone(b._disconnect_time)
        # port cleared for re-discovery (manual_port=False by default)
        self.assertIsNone(b.port)
        self.assertIsNone(b.serial_connection)

    def test_on_disconnect_keeps_manual_port(self):
        from arduino.bridge_button_dht11 import ArduinoButtonDHT11Bridge
        with patch("pathlib.Path.mkdir"):
            b = ArduinoButtonDHT11Bridge("dev", port="/dev/cu.fixed")
        b.serial_connection = MagicMock()
        b._on_disconnect("test")
        # manual_port=True → port must NOT be cleared
        self.assertEqual(b.port, "/dev/cu.fixed")

    def test_on_disconnect_does_not_overwrite_first_timestamp(self):
        b = self._make_bridge()
        b.serial_connection = MagicMock()
        b._on_disconnect("first")
        t1 = b._disconnect_time
        b._on_disconnect("second")
        self.assertEqual(b._disconnect_time, t1, "timestamp must not be overwritten")

    @patch("serial.tools.list_ports.comports", return_value=MOCK_PORTS)
    def test_reconnect_increments_stats_and_resets_state(self, _mock):
        b = self._make_bridge()
        import time as _time
        b._disconnect_time = _time.time() - 10  # simulate 10s downtime
        b._reconnect_attempts = 3
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = MagicMock()
            result = b.connect()
        self.assertTrue(result)
        # After connect() the run() loop resets state — simulate that:
        if b._disconnect_time is not None:
            b.stats["reconnects"] += 1
            b._disconnect_time = None
            b._reconnect_attempts = 0
        self.assertEqual(b.stats["reconnects"], 1)
        self.assertIsNone(b._disconnect_time)
        self.assertEqual(b._reconnect_attempts, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
