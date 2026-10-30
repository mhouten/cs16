#!/usr/bin/env python3
"""Create an amd64 COFF icon resource for the Go Windows launcher."""
from pathlib import Path
import struct
import sys


def resource_object(icon):
    reserved, kind, count = struct.unpack_from('<HHH', icon)
    if (reserved, kind) != (0, 1) or count < 1:
        raise ValueError('Expected a Windows ICO file')
    entries = []
    group = bytearray(struct.pack('<HHH', 0, 1, count))
    for index in range(count):
        width, height, colors, zero, planes, bits, size, offset = struct.unpack_from('<BBBBHHII', icon, 6 + index * 16)
        payload = icon[offset:offset + size]
        if len(payload) != size:
            raise ValueError('Truncated ICO image')
        entries.append((index + 1, payload))
        group.extend(struct.pack('<BBBBHHIH', width, height, colors, zero, planes, bits, size, index + 1))
    tree = {3: {key: {1033: data} for key, data in entries}, 14: {1: {1033: bytes(group)}}}
    data = bytearray()
    relocations = []

    def align():
        data.extend(b'\0' * (-len(data) % 4))

    def directory(children):
        align()
        start = len(data)
        data.extend(struct.pack('<IIHHHH', 0, 0, 0, 0, 0, len(children)))
        data.extend(b'\0' * (8 * len(children)))
        for index, (key, value) in enumerate(sorted(children.items())):
            if isinstance(value, dict):
                offset = directory(value) | 0x80000000
            else:
                align()
                offset = len(data)
                data.extend(b'\0' * 16)
                align()
                payload_offset = len(data)
                data.extend(value)
                struct.pack_into('<IIII', data, offset, payload_offset, len(value), 0, 0)
                relocations.append(offset)
            struct.pack_into('<II', data, start + 16 + index * 8, key, offset)
        return start

    directory(tree)
    align()
    raw_offset = 60
    relocation_offset = raw_offset + len(data)
    symbols_offset = relocation_offset + 10 * len(relocations)
    coff = struct.pack('<HHIIIHH', 0x8664, 1, 0, symbols_offset, 1, 0, 0)
    section = struct.pack('<8sIIIIIIHHI', b'.rsrc\0\0\0', 0, 0, len(data), raw_offset,
                          relocation_offset, 0, len(relocations), 0, 0x40300040)
    relocs = b''.join(struct.pack('<IIH', offset, 0, 3) for offset in relocations)
    symbol = struct.pack('<8sIhHBB', b'.rsrc\0\0\0', 0, 1, 0, 3, 0)
    return coff + section + data + relocs + symbol + struct.pack('<I', 4)


if __name__ == '__main__':
    Path(sys.argv[2]).write_bytes(resource_object(Path(sys.argv[1]).read_bytes()))
