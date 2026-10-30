#!/usr/bin/env python3
"""Convert supplied PNG artwork to native app icon containers using macOS sips."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    target = args.output / 'Source.png'
    if source != target.resolve():
        shutil.copyfile(source, target)
    sizes = [16, 24, 32, 48, 64, 128, 256, 512, 1024]
    with tempfile.TemporaryDirectory() as temporary:
        images = {}
        for size in sizes:
            path = Path(temporary) / f'{size}.png'
            subprocess.run(['sips', '-z', str(size), str(size), str(source), '--out', str(path)],
                           check=True, stdout=subprocess.DEVNULL)
            images[size] = path.read_bytes()
        shutil.copyfile(Path(temporary) / '512.png', args.output / 'CounterStrike.png')
        chunks = []
        for kind, size in [('icp4', 16), ('icp5', 32), ('icp6', 64), ('ic07', 128),
                           ('ic08', 256), ('ic09', 512), ('ic10', 1024)]:
            data = images[size]
            chunks.append(kind.encode() + struct.pack('>I', len(data) + 8) + data)
        payload = b''.join(chunks)
        (args.output / 'CounterStrike.icns').write_bytes(b'icns' + struct.pack('>I', len(payload) + 8) + payload)
        ico_sizes = [16, 24, 32, 48, 64, 128, 256]
        offset = 6 + 16 * len(ico_sizes)
        entries, payloads = [], []
        for size in ico_sizes:
            data = images[size]
            entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
            payloads.append(data)
            offset += len(data)
        (args.output / 'CounterStrike.ico').write_bytes(struct.pack('<HHH', 0, 1, len(ico_sizes)) + b''.join(entries) + b''.join(payloads))
    manifest = {'source': 'User-provided high-resolution PNG', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'mac_representations': [16, 32, 64, 128, 256, 512, 1024], 'windows_representations': ico_sizes,
                'linux_png_pixels': 512}
    (args.output / 'icon-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Created Mac ICNS, Windows ICO and Linux PNG:', args.output)


if __name__ == '__main__':
    main()
