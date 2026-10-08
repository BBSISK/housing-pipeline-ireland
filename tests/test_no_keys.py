"""Keyless from the first commit: no module may read an API key or password setting.

Azure access uses DefaultAzureCredential (managed identity in Azure, OIDC in CI,
az login on the laptop). This test fails if code starts reading key-style settings.
"""

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
FORBIDDEN = re.compile(
    r"(API_KEY|ACCOUNT_KEY|CONNECTION_STRING|SUBSCRIPTION_KEY|PASSWORD|SAS_TOKEN)",
    re.IGNORECASE,
)


def test_no_module_reads_key_settings():
    offenders = []
    for path in SRC.rglob("*.py"):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if "environ" in line or "getenv" in line:
                if FORBIDDEN.search(line):
                    offenders.append(f"{path.relative_to(SRC)}:{lineno}")
    assert not offenders, f"Key-style settings read in: {offenders}"
