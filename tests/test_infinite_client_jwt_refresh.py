import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from skills.infinite.scripts.infinite_client import InfiniteClient


def _mock_response(status_code: int, payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(payload)
    resp.json.return_value = payload
    return resp


class TestInfiniteClientJwtRefresh(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cfg_file = Path(self._tmp.name) / 'infinite_config.json'

    def tearDown(self):
        self._tmp.cleanup()

    @patch('skills.infinite.scripts.infinite_client.requests.post')
    def test_create_post_refreshes_expired_jwt_on_401_and_persists_new_token(self, mock_post):
        self.cfg_file.write_text(json.dumps({
            'api_key': 'inf_valid_key',
            'token': 'expired_jwt',
            'api_base': 'http://infinite.test/api',
        }))

        client = InfiniteClient(config_file=self.cfg_file)
        mock_post.assert_not_called()

        mock_post.side_effect = [
            _mock_response(401, {'error': 'Token expired'}),
            _mock_response(200, {'token': 'fresh_jwt'}),
            _mock_response(201, {'id': 'post-123'}),
        ]

        result = client.create_post(
            community='biology',
            title='BTK Kinase Selectivity',
            content='Summary of selectivity findings',
        )

        self.assertEqual(result, {'id': 'post-123'})
        self.assertEqual(client.jwt_token, 'fresh_jwt')
        saved = json.loads(self.cfg_file.read_text())
        self.assertEqual(saved['token'], 'fresh_jwt')

        self.assertEqual(mock_post.call_count, 3)
        first_post_headers = mock_post.call_args_list[0].kwargs['headers']
        retry_post_headers = mock_post.call_args_list[2].kwargs['headers']
        self.assertEqual(first_post_headers['Authorization'], 'Bearer expired_jwt')
        self.assertEqual(retry_post_headers['Authorization'], 'Bearer fresh_jwt')

    @patch('skills.infinite.scripts.infinite_client.requests.post')
    @patch('skills.infinite.scripts.infinite_client.requests.get')
    def test_get_notifications_refreshes_expired_jwt_on_401(self, mock_get, mock_post):
        self.cfg_file.write_text(json.dumps({
            'api_key': 'inf_valid_key',
            'token': 'expired_jwt',
            'api_base': 'http://infinite.test/api',
        }))

        client = InfiniteClient(config_file=self.cfg_file)
        mock_get.side_effect = [
            _mock_response(401, {'error': 'Token expired'}),
            _mock_response(200, {'notifications': [{'id': 'n1'}], 'unreadCount': 1}),
        ]
        mock_post.return_value = _mock_response(200, {'token': 'fresh_jwt_2'})

        result = client.get_notifications()

        self.assertEqual(result['unreadCount'], 1)
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_get.call_args_list[1].kwargs['headers']['Authorization'], 'Bearer fresh_jwt_2')

    @patch('skills.infinite.scripts.infinite_client.requests.post')
    def test_create_post_logs_in_lazily_when_initial_login_failed(self, mock_post):
        self.cfg_file.write_text(json.dumps({
            'api_key': 'inf_valid_key',
            'api_base': 'http://infinite.test/api',
        }))

        # Initial _login() in __init__ fails transiently (HTTP 503), then succeeds on create_post()
        mock_post.side_effect = [
            _mock_response(503, {'error': 'Service temporarily unavailable'}),
            _mock_response(200, {'token': 'recovered_jwt'}),
            _mock_response(201, {'id': 'post-456'}),
        ]

        client = InfiniteClient(config_file=self.cfg_file)
        self.assertIsNone(client.jwt_token)

        result = client.create_post(
            community='chemistry',
            title='Kinase Screen',
            content='Recovered after transient login failure',
        )

        self.assertEqual(result, {'id': 'post-456'})
        self.assertEqual(client.jwt_token, 'recovered_jwt')


if __name__ == '__main__':
    unittest.main()
