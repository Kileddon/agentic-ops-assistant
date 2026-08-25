from secrets import compare_digest

from agentic_ops_assistant.auth.models import ApiRole, Principal


class StaticApiKeyAuthenticator:
    def __init__(
        self,
        *,
        operator_key: str,
        approver_key: str,
        auditor_key: str,
    ) -> None:
        self._keys = {
            ApiRole.OPERATOR: _normalized_key(operator_key, "Operator"),
            ApiRole.APPROVER: _normalized_key(approver_key, "Approver"),
            ApiRole.AUDITOR: _normalized_key(auditor_key, "Auditor"),
        }

        if len(set(self._keys.values())) != len(self._keys):
            raise ValueError("API keys for different roles must be distinct.")

    def authenticate(self, api_key: str) -> Principal | None:
        for role, expected_key in self._keys.items():
            if compare_digest(api_key, expected_key):
                return Principal(role)

        return None


def _normalized_key(value: str, role_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{role_name} API key must not be blank.")

    return value
