from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "signed-windows-release.yml"
SCHEMA = ROOT / "docs" / "telemetry" / "update-event.schema.json"
VERIFY = ROOT / "scripts" / "verify-signed-artifact.ps1"
SCAN = ROOT / "scripts" / "scan-release-artifact.ps1"


def main() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    required_workflow_markers = (
        "id-token: write",
        "environment: production-signing",
        "azure/login@v3",
        "azure/artifact-signing-action@v2",
        "timestamp-rfc3161",
        "verify-signed-artifact.ps1",
        "scan-release-artifact.ps1",
        "Upload signing evidence retention copy",
        "Checkout release controls at signed tag",
        "Verify checked-out tag matches build provenance",
        "commit_sha: ${{ steps.meta.outputs.commit_sha }}",
    )
    for marker in required_workflow_markers:
        assert marker in workflow, f"Missing workflow control: {marker}"
    assert "AZURE_CLIENT_SECRET" not in workflow, "Long-lived Azure client secret must not be used."
    assert "azure-client-secret" not in workflow, "Credentialless OIDC workflow must not request a client secret."

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required_event_fields = {
        "schema_version",
        "event_id",
        "occurred_at_utc",
        "event_name",
        "installation_pseudonym",
        "tenant_pseudonym",
        "release_channel",
        "from_version",
        "to_version",
        "result",
    }
    assert required_event_fields.issubset(schema["properties"]), "Telemetry schema misses required fields."
    assert schema["additionalProperties"] is False, "Telemetry must reject ungoverned fields."
    assert "hostname" not in schema["properties"], "Telemetry must not collect hostnames."
    assert "user_name" not in schema["properties"], "Telemetry must not collect user names."

    verify = VERIFY.read_text(encoding="utf-8")
    scan = SCAN.read_text(encoding="utf-8")
    assert "Get-AuthenticodeSignature" in verify
    assert "TimeStamperCertificate" in verify
    assert "Get-FileHash" in verify
    assert "MpCmdRun.exe" in scan
    assert "-ScanType 3" in scan

    print("Release security asset validation passed")


if __name__ == "__main__":
    main()
