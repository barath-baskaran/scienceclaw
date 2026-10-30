import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from coordination.autonomous_orchestrator import AutonomousOrchestrator


def _load_investigate_cli():
    cli_path = Path(__file__).resolve().parent.parent / 'bin' / 'scienceclaw-investigate'
    loader = importlib.machinery.SourceFileLoader('scienceclaw_investigate_cli', str(cli_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class TestOrchestratorDryRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(os.environ, {'HOME': self._tmp.name})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self._tmp.cleanup()

    def test_investigate_dry_run_skips_posting_synthesis(self):
        orch = AutonomousOrchestrator()
        orch._analyze_topic = MagicMock(return_value={
            'investigation_type': 'mechanism-elucidation',
            'collaboration_pattern': 'sequential',
            'agents': [{'role': 'investigator', 'domain': 'biology', 'primary_skills': ['pubmed']}],
        })
        orch._spawn_agents = MagicMock(return_value=[{'name': 'BioAgent-1', 'role': 'investigator'}])
        orch._create_collaborative_session = MagicMock(return_value='session-123')
        orch._facilitate_collaboration = MagicMock(return_value={'results': {}, 'shared_memory': {}, 'discussion': []})
        orch._synthesize_findings = MagicMock(return_value={
            'synthesis_text': 'Synthesized findings',
            'key_findings': ['Finding 1'],
            'tools_used': ['pubmed'],
        })
        orch._post_synthesis = MagicMock(return_value='post-999')
        orch.session_manager.complete_session = MagicMock(return_value={'status': 'complete'})

        result = orch.investigate(
            topic='CRISPR specificity',
            community='biology',
            dry_run=True,
        )

        orch._post_synthesis.assert_not_called()
        self.assertIsNone(result['post_id'])
        orch.session_manager.complete_session.assert_called_once_with(
            session_id='session-123',
            summary='Synthesized findings',
            post_id=None,
        )

    def test_cli_forwards_dry_run_to_orchestrator(self):
        cli_mod = _load_investigate_cli()
        mock_orch_instance = MagicMock()
        mock_orch_instance.investigate.return_value = {
            'strategy': {
                'investigation_type': 'mechanism-elucidation',
                'collaboration_pattern': 'sequential',
            },
            'agents': ['BioAgent-1'],
            'session_id': 'session-123',
            'post_id': None,
            'synthesis': {
                'key_findings': ['Finding 1'],
                'tools_used': ['pubmed'],
            },
        }

        with patch.object(cli_mod, 'AutonomousOrchestrator', return_value=mock_orch_instance), \
             patch.object(sys, 'argv', ['scienceclaw-investigate', 'CRISPR specificity', '--community', 'biology', '--dry-run']):
            rc = cli_mod.main()

        self.assertEqual(rc, 0)
        mock_orch_instance.investigate.assert_called_once_with(
            topic='CRISPR specificity',
            community='biology',
            dry_run=True,
        )


if __name__ == '__main__':
    unittest.main()
