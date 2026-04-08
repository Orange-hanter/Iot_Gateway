#!/usr/bin/env python3
"""Диагностика: почему auto-discovery не находит Arduino."""
import serial.tools.list_ports

ARDUINO_VIDS = [0x2341, 0x2A03]
ARDUINO_KEYWORDS = ["arduino", "mega", "ch340", "ch341", "cp210", "ftdi", "usb serial"]

ports = serial.tools.list_ports.comports()
print(f"Total serial ports visible to pyserial: {len(ports)}\n")

for p in ports:
    vid_str = hex(p.vid) if p.vid else "None"
    pid_str = hex(p.pid) if p.pid else "None"
    print(f"  [{p.device}]")
    print(f"    description  : {p.description}")
    print(f"    hwid         : {p.hwid}")
    print(f"    vid:pid      : {vid_str}:{pid_str}")
    print(f"    serial_number: {p.serial_number}")
    print(f"    manufacturer : {p.manufacturer}")

    match_vid = p.vid in ARDUINO_VIDS
    match_kw  = p.description and any(k in p.description.lower() for k in ARDUINO_KEYWORDS)
    print(f"    --> VID match: {match_vid}  keyword match: {match_kw}  SELECTED: {match_vid or match_kw}")
    print()

if not ports:
    print("No ports at all — Arduino is not connected or driver is missing.")
