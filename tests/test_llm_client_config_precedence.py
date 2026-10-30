import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.llm_client import LLMClient


class TestLLMClientConfigPrecedence(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.cfg_dir = self.home / '.scienceclaw'
        self.cfg_dir.mkdir(parents=True, exist_ok=True)
        self.cfg_path = self.cfg_dir / 'llm_config.json'

    def tearDown(self):
        self._tmp.cleanup()

    def _clean_llm_env(self):
        keys = (
            'LLM_BACKEND',
            'OPENAI_API_KEY',
            'OPENAI_MODEL',
            'OPENAI_BASE_URL',
            'ANTHROPIC_API_KEY',
            'ANTHROPIC_MODEL',
            'GEMINI_API_KEY',
            'GOOGLE_API_KEY',
            'GEMINI_MODEL',
            'GEMINI_BASE_URL',
            'GEMINI_REASONING_EFFORT',
            'GEMINI_THINKING_HEADROOM',
            'GEMINI_MAX_RETRIES',
            'GEMINI_SYSTEM_PROMPT',
            'HF_API_KEY',
            'HUGGINGFACE_API_KEY',
            'HF_MODEL',
            'HF_ENDPOINT',
            'LLM_TIMEOUT',
        )
        return {k: v for k, v in os.environ.items() if k not in keys}

    @patch.object(LLMClient, '_init_gemini', lambda self: None)
    @patch.object(LLMClient, '_init_openai', lambda self: None)
    def test_env_vars_override_saved_llm_config(self):
        self.cfg_path.write_text(json.dumps({
            'backend': 'openai',
            'openai_api_key': 'sk-from-config',
            'gemini_api_key': 'gem-from-config',
            'gemini_model': 'gemini-2.5-flash',
            'gemini_reasoning_effort': 'medium',
        }))

        env = self._clean_llm_env()
        env.update({
            'HOME': str(self.home),
            'LLM_BACKEND': 'gemini',
            'GEMINI_API_KEY': 'gem-from-env',
            'GEMINI_MODEL': 'gemini-3.6-flash',
            'GEMINI_REASONING_EFFORT': '',
        })
        with patch.dict(os.environ, env, clear=True):
            client = LLMClient(agent_name='EnvOverrideAgent')

        self.assertEqual(client.backend, 'gemini')
        self.assertEqual(client.gemini_key, 'gem-from-env')
        self.assertEqual(client.gemini_model, 'gemini-3.6-flash')
        self.assertEqual(client.gemini_reasoning_effort, '')

    @patch.object(LLMClient, '_init_gemini', lambda self: None)
    @patch.object(LLMClient, '_init_openai', lambda self: None)
    def test_explicit_backend_arg_overrides_config_and_env(self):
        self.cfg_path.write_text(json.dumps({
            'backend': 'openai',
            'openai_api_key': 'sk-from-config',
            'gemini_api_key': 'gem-from-config',
        }))

        env = self._clean_llm_env()
        env.update({
            'HOME': str(self.home),
            'LLM_BACKEND': 'openai',
        })
        with patch.dict(os.environ, env, clear=True):
            client = LLMClient(agent_name='ExplicitBackendAgent', backend='gemini')

        self.assertEqual(client.backend, 'gemini')
        self.assertEqual(client.gemini_key, 'gem-from-config')

    @patch.object(LLMClient, '_init_gemini', lambda self: None)
    def test_saved_llm_config_used_when_env_vars_absent(self):
        self.cfg_path.write_text(json.dumps({
            'backend': 'gemini',
            'gemini_api_key': 'gem-from-config',
            'gemini_model': 'gemini-2.5-pro',
            'timeout': 90,
        }))

        env = self._clean_llm_env()
        env['HOME'] = str(self.home)
        with patch.dict(os.environ, env, clear=True):
            client = LLMClient(agent_name='ConfigFallbackAgent')

        self.assertEqual(client.backend, 'gemini')
        self.assertEqual(client.gemini_key, 'gem-from-config')
        self.assertEqual(client.gemini_model, 'gemini-2.5-pro')
        self.assertEqual(client.timeout, 90)


if __name__ == '__main__':
    unittest.main()
