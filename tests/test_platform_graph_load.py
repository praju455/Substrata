"""The synthetic graph-query load harness remains runnable from CI and local shells."""

import json
import subprocess
import sys


def test_platform_graph_load_smoke():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.platform_graph_load",
            "--nodes",
            "63",
            "--queries",
            "8",
            "--workers",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["data_label"] == "synthetic only"
    assert report["nodes"] == 63
    assert report["edges"] == 62
    assert report["queries"] == 8
    assert report["latency_ms"]["p95"] >= 0
