from __future__ import annotations

import locale
import subprocess


def _decode_output(data: bytes) -> str:
    if not data:
        return ""

    preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
    for encoding in ("utf-8", preferred_encoding, "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=False, check=False)
    return subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=_decode_output(result.stdout),
        stderr=_decode_output(result.stderr),
    )
