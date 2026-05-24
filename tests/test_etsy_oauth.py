import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from planner_generator.etsy_integration.oauth import env_lines_for_tokens, finish_oauth_flow, refresh_oauth_token, start_oauth_flow


class FakeOAuthTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, url, headers, payload):
        raise AssertionError("OAuth should use form posts.")

    def post_form(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.response


def test_start_oauth_flow_writes_pkce_state_and_authorization_url(tmp_path):
    result = start_oauth_flow(
        api_key="api-key",
        redirect_uri="http://localhost:8080/callback",
        state_path=tmp_path / "oauth_state.json",
    )

    query = parse_qs(urlparse(result.authorization_url).query)
    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert query["client_id"] == ["api-key"]
    assert query["redirect_uri"] == ["http://localhost:8080/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [state["state"]]
    assert state["code_verifier"]


def test_finish_oauth_flow_exchanges_code_and_writes_tokens(tmp_path):
    state = start_oauth_flow("api-key", "http://localhost:8080/callback", tmp_path / "oauth_state.json")
    transport = FakeOAuthTransport({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600})

    result = finish_oauth_flow(
        code="returned-code",
        state_path=state.state_path,
        output_path=tmp_path / "oauth_tokens.json",
        transport=transport,
    )

    assert result.tokens["access_token"] == "access"
    assert result.output_path.exists()
    assert transport.calls[0]["payload"]["grant_type"] == "authorization_code"
    assert transport.calls[0]["payload"]["code_verifier"] == state.state["code_verifier"]
    assert "ETSY_ACCESS_TOKEN=access" in env_lines_for_tokens(result.tokens)


def test_refresh_oauth_token_writes_refreshed_tokens(tmp_path):
    transport = FakeOAuthTransport({"access_token": "new-access", "refresh_token": "new-refresh"})

    result = refresh_oauth_token("api-key", "old-refresh", tmp_path / "oauth_tokens.json", transport=transport)

    assert result.tokens["access_token"] == "new-access"
    assert transport.calls[0]["payload"] == {
        "grant_type": "refresh_token",
        "client_id": "api-key",
        "refresh_token": "old-refresh",
    }
