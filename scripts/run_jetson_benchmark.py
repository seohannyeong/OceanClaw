"""Run an isolated local API and benchmark on a real Jetson; stop our API on exit."""
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    device = Path("/proc/device-tree/model")
    if not device.exists() or "jetson" not in device.read_text().lower():
        parser.error("Run this script on Jetson, not the desktop.")
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    out = ROOT / "output/eval"
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / ("jetson_api_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".log")
    env = {**os.environ, "OLLAMA_TIMEOUT": "600"}
    url = f"http://127.0.0.1:{args.port}"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "scripts/run_api.py", "--host", "127.0.0.1", "--port", str(args.port)],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError(f"API startup failed; see {log_path}")
                try:
                    with urllib.request.urlopen(url + "/openapi.json", timeout=2):
                        break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError(f"API startup timed out; see {log_path}")
            return subprocess.call([sys.executable, "scripts/validate_holdout.py", "--api-url", url,
                "--require-jetson", "--limit", str(args.limit), "--repeats", str(args.repeats), "--timeout", "660"], cwd=ROOT, env=env)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            print(f"Temporary API stopped. Server log: {log_path}")


if __name__ == "__main__":
    raise SystemExit(main())
