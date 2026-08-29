import jwt

from agentic_ops_assistant.auth.keycloak import KeycloakJwtAuthenticator
from agentic_ops_assistant.auth.models import ApiRole


def test_keycloak_authenticator_maps_a_single_realm_role() -> None:
    authenticator = KeycloakJwtAuthenticator(
        issuer="https://identity.example/realms/ops",
        audience="ops-api",
        decoder=lambda token: {"realm_access": {"roles": ["operator"]}},
    )

    principal = authenticator.authenticate("access-token")

    assert principal is not None
    assert principal.role == ApiRole.OPERATOR


def test_keycloak_authenticator_rejects_invalid_or_ambiguous_roles() -> None:
    invalid_token_authenticator = KeycloakJwtAuthenticator(
        issuer="https://identity.example/realms/ops",
        audience="ops-api",
        decoder=lambda token: (_ for _ in ()).throw(jwt.InvalidTokenError()),
    )
    ambiguous_roles_authenticator = KeycloakJwtAuthenticator(
        issuer="https://identity.example/realms/ops",
        audience="ops-api",
        decoder=lambda token: {"realm_access": {"roles": ["operator", "auditor"]}},
    )

    assert invalid_token_authenticator.authenticate("invalid") is None
    assert ambiguous_roles_authenticator.authenticate("access-token") is None


def test_keycloak_authenticator_accepts_a_separate_jwks_url() -> None:
    authenticator = KeycloakJwtAuthenticator(
        issuer="http://127.0.0.1:8080/realms/ops",
        audience="ops-api",
        jwks_url="http://host.docker.internal:8080/realms/ops/protocol/openid-connect/certs",
        decoder=lambda token: {"realm_access": {"roles": ["operator"]}},
    )

    principal = authenticator.authenticate("access-token")

    assert principal is not None
    assert principal.role == ApiRole.OPERATOR
