import httpx
import pytest

from app.services.dexcom import DexcomOAuthError, raise_for_oauth_error


def test_oauth_error_includes_dexcom_code_and_description():
    response = httpx.Response(
        400,
        json={
            "error": "invalid_client",
            "error_description": "Client authentication failed",
        },
    )

    with pytest.raises(
        DexcomOAuthError,
        match="invalid_client.*Client authentication failed",
    ):
        raise_for_oauth_error(response)


def test_oauth_success_does_not_raise():
    raise_for_oauth_error(httpx.Response(200, json={"access_token": "token"}))
