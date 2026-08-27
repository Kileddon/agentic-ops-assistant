from secrets import compare_digest

from agentic_ops_assistant.auth.models import ApiRole, Principal


class StaticApiKeyAuthenticator:
    def __init__(
        self,
        *,
        operator_key: str,
        approver_key: str,
        auditor_key: str,
        operator_next_key: str | None = None,
        approver_next_key: str | None = None,
        auditor_next_key: str | None = None,
    ) -> None:
        self._keys = {
            ApiRole.OPERATOR: _role_keys(operator_key, operator_next_key, "Operator"),
            ApiRole.APPROVER: _role_keys(approver_key, approver_next_key, "Approver"),
            ApiRole.AUDITOR: _role_keys(auditor_key, auditor_next_key, "Auditor"),
        }
        all_keys = tuple(key for role_keys in self._keys.values() for key in role_keys)

        if len(set(all_keys)) != len(all_keys):
            raise ValueError("API keys, including rotation keys, must be distinct.")

    def authenticate(self, api_key: str) -> Principal | None:
        for role, expected_keys in self._keys.items():
            for expected_key in expected_keys:
                if compare_digest(api_key, expected_key):
                    return Principal(role)

        return None


def _normalized_key(value: str, role_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{role_name} API key must not be blank.")

    return value


def _role_keys(
    current_key: str,
    next_key: str | None,
    role_name: str,
) -> tuple[str, ...]:
    normalized_current_key = _normalized_key(current_key, role_name)

    if next_key is None:
        return (normalized_current_key,)

    return (normalized_current_key, _normalized_key(next_key, role_name))
