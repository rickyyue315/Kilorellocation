import hashlib
import json
import logging
import os
from typing import Optional

import httpx

import config

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_OUTSIDE_STREAMLIT_CACHE: dict = {}


def get_secret_or_env(name: str, default: str = '') -> str:
    try:
        import streamlit as st
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        pass
    return os.getenv(name, default)


def _get_api_key() -> str:
    key = get_secret_or_env('OPENROUTER_API_KEY', '')
    if key:
        return key
    return os.getenv('OPENROUTER_API_KEY', '')


def _get_env_bool_override(name: str, config_value: bool) -> bool:
    env_val = get_secret_or_env(name, '')
    if not env_val:
        return config_value
    if isinstance(env_val, bool):
        return env_val
    if isinstance(env_val, str):
        return env_val.strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    return config_value


def is_ai_enabled() -> bool:
    return _get_env_bool_override('AI_ENABLED', config.AI_ENABLED) and bool(_get_api_key())


def get_ai_status() -> dict:
    enabled = _get_env_bool_override('AI_ENABLED', config.AI_ENABLED)
    has_key = bool(_get_api_key())
    if not enabled:
        return {'enabled': False, 'has_api_key': has_key, 'model': '', 'reason': 'AI is disabled (AI_ENABLED=false)'}
    if not has_key:
        return {'enabled': False, 'has_api_key': False, 'model': '', 'reason': 'No API key configured'}
    return {'enabled': True, 'has_api_key': True, 'model': config.AI_DEFAULT_MODEL, 'reason': ''}


def _make_cache_key(messages: list, model: str, temperature: float, max_tokens: int, namespace: str) -> str:
    payload = {
        'messages': messages,
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{namespace}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _get_cache() -> dict:
    try:
        import streamlit as st
        return st.session_state.setdefault('_ai_cache', {})
    except Exception:
        pass
    return _OUTSIDE_STREAMLIT_CACHE


def chat_completion(
    messages: list,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    cache_namespace: str = 'default',
) -> str:
    if not is_ai_enabled():
        return ''

    api_key = _get_api_key()
    if not api_key:
        logger.warning("AI chat_completion skipped: no API key")
        return ''

    model_name = model or config.AI_DEFAULT_MODEL
    cache_key = _make_cache_key(messages, model_name, temperature, max_tokens, cache_namespace)
    cache = _get_cache()
    if cache_key in cache:
        return cache[cache_key]

    content = _do_request(model_name, messages, temperature, max_tokens, api_key)

    if content:
        cache[cache_key] = content
    else:
        logger.warning("chat_completion returned empty for model %s", model_name)
    return content

def _do_request(model_name: str, messages: list, temperature: float, max_tokens: int, api_key: str) -> str:
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': os.getenv('OPENROUTER_SITE_URL', ''),
        'X-Title': os.getenv('OPENROUTER_APP_TITLE', 'KiLo Reallocation'),
    }
    body = {
        'model': model_name,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }

    try:
        client = httpx.Client(timeout=float(config.AI_REQUEST_TIMEOUT))
        resp = client.post(_OPENROUTER_URL, json=body, headers=headers)
        client.close()

        logger.info("OpenRouter HTTP %d (%s)", resp.status_code, model_name)

        if not resp.is_success:
            logger.warning("OpenRouter HTTP %d (%s): %s", resp.status_code, model_name, resp.text[:200])
            return ''

        data = resp.json()
        choices = data.get('choices', [])
        if not choices:
            logger.warning("OpenRouter response missing choices (%s)", model_name)
            return ''

        message = choices[0].get('message', {}) or {}
        content = (message.get('content') or '').strip()
        if not content:
            logger.warning("OpenRouter returned empty content (%s): %s", model_name, json.dumps(data, ensure_ascii=False)[:500])
        return content

    except httpx.TimeoutException:
        logger.warning("OpenRouter request timed out after %ds (%s)", config.AI_REQUEST_TIMEOUT, model_name)
        return ''
    except httpx.HTTPError as e:
        logger.warning("OpenRouter HTTP error (%s): %s", model_name, type(e).__name__)
        return ''
    except Exception:
        logger.warning("OpenRouter request failed (%s)", model_name, exc_info=True)
        return ''
