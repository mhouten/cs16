#!/usr/bin/env python3
"""Read real native Mac server cvars after switching every optional host mode."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    definitions = json.loads((Path(__file__).resolve().parent.parent / 'Features/modes.json').read_text())
    reset = definitions['reset']
    probes = []
    for name, info in definitions['modes'].items():
        probes += ['mode_' + name, 'echo CHECK_' + name, *reset, 'echo END_' + name,
                   'mode_classic', 'echo RESET_' + name, *reset, 'echo RESET_END_' + name]
    script = 'exec optional_modes.cfg\n' + '\n'.join(probes) + '\necho ALL_MODE_CHECKS_COMPLETE\n'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    logfile = args.report.with_suffix('.log')
    with tempfile.TemporaryDirectory(prefix='cs16-mode-runtime-') as tmp:
        saved = Path(tmp) / 'cstrike'
        saved.mkdir()
        (saved / 'mode-probe.cfg').write_text(script)
        (saved / 'server.cfg').write_text('exec modes/_reset.cfg\nexec gwlistenserver.cfg\nexec mode-probe.cfg\n')
        env = dict(os.environ, CS16_USERDIR=tmp, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        with logfile.open('wb') as log:
            process = subprocess.Popen([str(args.app.resolve() / 'Contents/MacOS/CounterStrike'),
                                        '-dedicated', '-noip', '-noip6', '+maxplayers', '16', '+map', 'de_dust2'],
                                       env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                while process.poll() is None and time.monotonic() < deadline:
                    output = logfile.read_text(errors='replace')
                    if 'ALL_MODE_CHECKS_COMPLETE' in output and '16 player server started' in output:
                        break
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
    output = re.sub(r'\x1b\[[0-9;]*m', '', logfile.read_text(errors='replace'))
    output = re.sub(r'(?m)^\[\d\d:\d\d:\d\d\]\s*', '', output)
    results = {}
    for name, info in definitions['modes'].items():
        for start, end, expected, label in [
                ('CHECK_' + name, 'END_' + name, {**reset, **info['values']}, name),
                ('RESET_' + name, 'RESET_END_' + name, reset, name + '_to_classic')]:
            match = re.search(r'(?m)^' + start + r'\s*$([\s\S]*?)^' + end + r'\s*$', output)
            assert match, 'Missing runtime marker: ' + start + '; see ' + str(logfile)
            observed = {}
            for variable, expected_value in expected.items():
                value = re.search(r'"?' + re.escape(variable) + r'"? is "([^"\r\n]*)"', match[1])
                assert value, 'No native cvar value for ' + variable + '; see ' + str(logfile)
                observed[variable] = value[1]
                try:
                    equal = float(value[1]) == float(expected_value)
                except (ValueError, TypeError):
                    equal = value[1] == str(expected_value)
                assert equal, f'{label}: {variable}={value[1]!r}, expected {expected_value!r}'
            results[label] = observed
    assert '16 player server started' in output, 'Map did not finish starting'
    for variable in reset:
        assert f'Unknown command "{variable}"' not in output, variable
    args.report.write_text(json.dumps({'native_modes_and_resets': results,
                                      'network_disabled': True, 'graphical_play_tested': False}, indent=2) + '\n')
    print('Native cvar checks passed for all nine host modes and nine Classic resets.')


if __name__ == '__main__':
    main()
