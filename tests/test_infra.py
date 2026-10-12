"""Static checks on the Terraform: keyless, least privilege, data protected. No Azure access needed."""

import pathlib
import re

INFRA = pathlib.Path(__file__).resolve().parents[1] / "infra"
RAW = "\n".join(p.read_text() for p in sorted(INFRA.glob("*.tf")))
TF = re.sub(r"#.*", "", RAW)  # check code, not comments
ALLOWED_ROLES = {"Storage Blob Data Contributor", "Storage Blob Data Reader"}


def test_storage_keys_are_off():
    assert re.search(r"shared_access_key_enabled\s*=\s*false", TF)
    assert re.search(r"storage_use_azuread\s*=\s*true", TF)


def test_only_data_plane_roles_are_assigned():
    roles = set(re.findall(r'role_definition_name\s*=\s*"([^"]+)"', TF))
    assert roles, "expected at least one role assignment"
    assert roles <= ALLOWED_ROLES, f"broad or unexpected roles: {roles - ALLOWED_ROLES}"
    assert "Owner" not in TF and '"Contributor"' not in TF


def test_containers_private_and_storage_protected():
    assert 'container_access_type = "private"' in TF
    assert re.search(r"allow_nested_items_to_be_public\s*=\s*false", TF)
    assert re.search(r"prevent_destroy\s*=\s*true", TF)


def test_data_stays_in_ireland_by_default():
    assert re.search(r'default\s*=\s*"northeurope"', TF)


def test_no_secrets_in_terraform():
    assert not re.search(r"(access_key|connection_string|client_secret|password)\s*=", TF, re.I)
