from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlencode

from planner_generator.etsy_integration.api import EtsyTransport, UrllibEtsyTransport


AUTHORIZATION_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
DEFAULT_SCOPES = ["listings_r", "listings_w", "shops_r"]
DEFAULT_OAUTH_STATE_PATH = ".etsy/oauth_state.json"


@dataclass(frozen=True)
class EtsyOAuthStartResult:
    authorization_url: str
    state_path: Path
    state: Dict[str, object]


@dataclass(frozen=True)
class EtsyOAuthTokenResult:
    output_path: Path
    tokens: Dict[str, object]


def start_oauth_flow(
    api_key: str,
    redirect_uri: str,
    state_path: str | Path = DEFAULT_OAUTH_STATE_PATH,
    scopes: List[str] | None = None,
) -> EtsyOAuthStartResult:
    if not api_key:
        raise ValueError("ETSY_API_KEY is required to start Etsy OAuth.")
    if not redirect_uri:
        raise ValueError("A redirect URI is required to start Etsy OAuth.")
    scopes = scopes or DEFAULT_SCOPES
    code_verifier = _token_urlsafe(64)
    state_value = _token_urlsafe(32)
    code_challenge = _code_challenge(code_verifier)
    state = {
        "api_key": api_key,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "state": state_value,
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
    }
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": api_key,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state_value,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return EtsyOAuthStartResult(
        authorization_url=f"{AUTHORIZATION_URL}?{query}",
        state_path=state_path,
        state=state,
    )


def finish_oauth_flow(
    code: str,
    state_path: str | Path = DEFAULT_OAUTH_STATE_PATH,
    output_path: str | Path = ".etsy/oauth_tokens.json",
    transport: EtsyTransport | None = None,
) -> EtsyOAuthTokenResult:
    if not code:
        raise ValueError("Authorization code is required to finish Etsy OAuth.")
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    transport = transport or UrllibEtsyTransport()
    tokens = transport.post_form(
        TOKEN_URL,
        {"Content-Type": "application/x-www-form-urlencoded"},
        {
            "grant_type": "authorization_code",
            "client_id": str(state["api_key"]),
            "redirect_uri": str(state["redirect_uri"]),
            "code": code,
            "code_verifier": str(state["code_verifier"]),
        },
    )
    return _write_tokens(tokens, output_path)


def refresh_oauth_token(
    api_key: str,
    refresh_token: str,
    output_path: str | Path = ".etsy/oauth_tokens.json",
    transport: EtsyTransport | None = None,
) -> EtsyOAuthTokenResult:
    if not api_key:
        raise ValueError("ETSY_API_KEY is required to refresh an Etsy token.")
    if not refresh_token:
        raise ValueError("ETSY_REFRESH_TOKEN is required to refresh an Etsy token.")
    transport = transport or UrllibEtsyTransport()
    tokens = transport.post_form(
        TOKEN_URL,
        {"Content-Type": "application/x-www-form-urlencoded"},
        {
            "grant_type": "refresh_token",
            "client_id": api_key,
            "refresh_token": refresh_token,
        },
    )
    return _write_tokens(tokens, output_path)


def env_lines_for_tokens(tokens: Dict[str, object]) -> List[str]:
    lines = []
    if tokens.get("access_token"):
        lines.append(f"ETSY_ACCESS_TOKEN={tokens['access_token']}")
    if tokens.get("refresh_token"):
        lines.append(f"ETSY_REFRESH_TOKEN={tokens['refresh_token']}")
    return lines


def _write_tokens(tokens: Dict[str, object], output_path: str | Path) -> EtsyOAuthTokenResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")
    return EtsyOAuthTokenResult(output_path=output_path, tokens=tokens)


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _token_urlsafe(length: int) -> str:
    return secrets.token_urlsafe(length)[:length]
