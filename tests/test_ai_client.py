import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class TestAIEnabledFalse:
    def test_chat_completion_returns_empty_when_disabled(self):
        with patch('services.ai_client.is_ai_enabled', return_value=False):
            from services.ai_client import chat_completion
            result = chat_completion([{'role': 'user', 'content': 'hello'}])
            assert result == ''


class TestNoAPIKey:
    def test_chat_completion_returns_empty_without_key(self):
        with patch('services.ai_client.is_ai_enabled', return_value=True), \
             patch('services.ai_client._get_api_key', return_value=''):
            from services.ai_client import chat_completion
            result = chat_completion([{'role': 'user', 'content': 'hello'}])
            assert result == ''


class TestMockHTTPSuccess:
    def test_returns_content_on_success(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Hello, world!'}}]
        }
        mock_response.status_code = 200

        with patch('services.ai_client.is_ai_enabled', return_value=True), \
             patch('services.ai_client._get_api_key', return_value='sk-test'), \
             patch('httpx.Client') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            from services.ai_client import chat_completion
            result = chat_completion([{'role': 'user', 'content': 'hello'}])
            assert result == 'Hello, world!'
            mock_client.post.assert_called_once()


class TestMockHTTPException:
    def test_returns_empty_on_http_error(self):
        with patch('services.ai_client.is_ai_enabled', return_value=True), \
             patch('services.ai_client._get_api_key', return_value='sk-test'), \
             patch('services.ai_client._get_cache', return_value={}), \
             patch('httpx.Client') as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = Exception("Connection error")
            mock_client.__enter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            from services.ai_client import chat_completion
            result = chat_completion([{'role': 'user', 'content': 'hello'}])
            assert result == ''


class TestCacheHit:
    def test_cache_hit_avoids_second_post(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'cached response'}}]
        }
        mock_response.status_code = 200

        with patch('services.ai_client.is_ai_enabled', return_value=True), \
             patch('services.ai_client._get_api_key', return_value='sk-test'), \
             patch('services.ai_client._OUTSIDE_STREAMLIT_CACHE', {}):
            from services.ai_client import chat_completion, _get_cache
            _get_cache().clear()

            with patch('httpx.Client') as mock_client_cls:
                mock_client = MagicMock()
                mock_client.post.return_value = mock_response
                mock_client.__enter__.return_value = mock_client
                mock_client_cls.return_value = mock_client

                msgs = [{'role': 'user', 'content': 'test cache'}]
                r1 = chat_completion(msgs)
                r2 = chat_completion(msgs)
                assert r1 == 'cached response'
                assert r2 == 'cached response'
                assert mock_client.post.call_count == 1


class TestGetSecretOrEnv:
    def test_safe_call_with_nonexistent_key_returns_empty(self):
        from services.ai_client import get_secret_or_env
        result = get_secret_or_env('__DOES_NOT_EXIST_ANYWHERE__')
        assert result == ''

    def test_falls_back_to_environ(self, monkeypatch):
        monkeypatch.setenv('TEST_SECRET_FALLBACK', 'env_value')
        from services.ai_client import get_secret_or_env
        result = get_secret_or_env('TEST_SECRET_FALLBACK')
        assert result == 'env_value'


class TestGetAIStatus:
    def test_disabled_when_env_false_and_no_key(self):
        with patch('services.ai_client._get_api_key', return_value=''), \
             patch('services.ai_client._get_env_bool_override', return_value=False):
            from services.ai_client import get_ai_status
            status = get_ai_status()
            assert status['enabled'] is False
