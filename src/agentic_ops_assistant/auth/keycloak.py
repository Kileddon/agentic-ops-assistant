from collections.abc import Callable, Mapping

import httpx2
import jwt

from agentic_ops_assistant.auth.models import ApiRole, Principal


class KeycloakJwtAuthenticator:
    """Authenticates Keycloak access tokens using the realm JWKS endpoint."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        decoder: Callable[[str], Mapping[str, object]] | None = None,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._jwks_url = (
            f"{self._issuer}/protocol/openid-connect/certs" if jwks_url is None else jwks_url
        )
        self._decoder = decoder or self._decode
        self._http_client = httpx2.Client(trust_env=False) if http_client is None else http_client

    def authenticate(self, token: str) -> Principal | None:
        try:
            payload = self._decoder(token)
        except (httpx2.HTTPError, jwt.PyJWTError):
            return None

        roles = _realm_roles(payload)
        api_roles = {ApiRole(role) for role in roles if role in ApiRole}

        if len(api_roles) != 1:
            return None

        return Principal(api_roles.pop())

    def _decode(self, token: str) -> Mapping[str, object]:
        response = self._http_client.get(self._jwks_url)
        response.raise_for_status()
        jwks_payload: object = response.json()

        if not isinstance(jwks_payload, dict):
            raise jwt.InvalidTokenError("Keycloak JWKS response must be an object.")

        key_id = jwt.get_unverified_header(token).get("kid")
        signing_key = next(
            (key for key in jwt.PyJWKSet.from_dict(jwks_payload).keys if key.key_id == key_id),
            None,
        )

        if signing_key is None:
            raise jwt.InvalidTokenError("No matching Keycloak signing key.")

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self._audience,
            issuer=self._issuer,
        )


def _realm_roles(payload: Mapping[str, object]) -> tuple[str, ...]:
    realm_access = payload.get("realm_access")

    if not isinstance(realm_access, Mapping):
        return ()

    raw_roles = realm_access.get("roles")

    if not isinstance(raw_roles, list):
        return ()

    return tuple(role for role in raw_roles if isinstance(role, str))
