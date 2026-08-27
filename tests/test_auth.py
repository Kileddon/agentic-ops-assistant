import pytest

from agentic_ops_assistant.auth.models import ApiRole
from agentic_ops_assistant.auth.service import StaticApiKeyAuthenticator


def test_authenticator_accepts_current_and_next_key_for_the_same_role() -> None:
    authenticator = StaticApiKeyAuthenticator(
        operator_key="operator-current",
        operator_next_key="operator-next",
        approver_key="approver-current",
        auditor_key="auditor-current",
    )

    current_principal = authenticator.authenticate("operator-current")
    next_principal = authenticator.authenticate("operator-next")

    assert current_principal is not None
    assert current_principal.role == ApiRole.OPERATOR
    assert next_principal is not None
    assert next_principal.role == ApiRole.OPERATOR
    assert authenticator.authenticate("unknown") is None


def test_authenticator_rejects_a_key_shared_across_roles_or_rotation_slots() -> None:
    with pytest.raises(
        ValueError,
        match="API keys, including rotation keys, must be distinct",
    ):
        StaticApiKeyAuthenticator(
            operator_key="operator-current",
            operator_next_key="replacement-key",
            approver_key="replacement-key",
            auditor_key="auditor-current",
        )
