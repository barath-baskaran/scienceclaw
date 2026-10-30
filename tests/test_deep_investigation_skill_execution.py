import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from autonomous.deep_investigation import DeepInvestigator


class TestDeepInvestigationSkillExecution(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / 'skills').mkdir(parents=True, exist_ok=True)

        inv = DeepInvestigator.__new__(DeepInvestigator)
        inv.agent_name = 'TestAgent'
        inv.agent_profile = None
        inv.scienceclaw_dir = self.root
        inv.journal = None
        inv.tracker = None
        inv.knowledge = None
        inv.llm_reasoner = None
        inv.skill_registry = MagicMock()
        inv.skill_selector = None
        inv.skill_executor = MagicMock()
        inv.topic_analyzer = None
        inv.artifact_store = None
        inv._current_investigation_id = ''
        inv._generate_insights = MagicMock(return_value=['synthesized insight'])
        self.inv = inv

    def tearDown(self):
        self._tmp.cleanup()

    def _write_skill_md(self, skill_name: str, content: str = '# Skill Docs\n') -> None:
        skill_dir = self.root / 'skills' / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / 'SKILL.md').write_text(content)

    def test_first_try_literature_skill_populates_papers_and_tools_used(self):
        self.inv.skill_registry.get_skill.return_value = {
            'name': 'pubmed',
            'category': 'literature',
            'executables': ['/fake/skills/pubmed/scripts/pubmed_search.py'],
        }
        self.inv.skill_executor.execute_skill.return_value = {
            'status': 'success',
            'result': {
                'papers': [
                    {'pmid': '12345', 'title': 'Ibrutinib kinase selectivity profile'}
                ]
            },
        }

        results = self.inv.run_tool_chain(
            topic='ibrutinib kinase selectivity',
            pre_selected_skills=[
                {
                    'name': 'pubmed',
                    'reason': 'Search literature on ibrutinib selectivity',
                    'suggested_params': {'query': 'ibrutinib kinase selectivity'},
                }
            ],
        )

        self.assertEqual(results['tools_used'], ['pubmed'])
        self.assertEqual(results['productive_tools'], ['pubmed'])
        self.assertEqual(len(results['papers']), 1)
        self.assertEqual(results['papers'][0]['pmid'], '12345')

    @patch('core.llm_client.get_llm_client')
    def test_script_name_does_not_leak_across_skill_iterations(self, mock_get_llm_client):
        self._write_skill_md('custom-runner', '# Custom Runner\n--code required\n')
        self._write_skill_md('pubmed', '# PubMed\n--query required\n')

        mock_llm = MagicMock()
        mock_llm.call.return_value = ''
        mock_get_llm_client.return_value = mock_llm

        skills_meta = {
            'custom-runner': {
                'name': 'custom-runner',
                'category': 'computation',
                'executables': ['/fake/skills/custom-runner/scripts/run_code.py'],
            },
            'pubmed': {
                'name': 'pubmed',
                'category': 'literature',
                'executables': ['/fake/skills/pubmed/scripts/pubmed_search.py'],
            },
        }
        self.inv.skill_registry.get_skill.side_effect = skills_meta.get
        self.inv.skill_executor.execute_skill.side_effect = [
            {
                'status': 'error',
                'error': 'error: the following arguments are required: --code',
            },
            {
                'status': 'success',
                'result': {
                    'return_code': 1,
                    'stderr': 'non-fatal warning',
                    'papers': [{'pmid': '99999', 'title': 'BTK selectivity study'}],
                },
            },
        ]

        results = self.inv.run_tool_chain(
            topic='BTK selectivity',
            pre_selected_skills=[
                {'name': 'custom-runner', 'reason': 'run snippet', 'suggested_params': {}},
                {'name': 'pubmed', 'reason': 'find papers', 'suggested_params': {'query': 'BTK selectivity'}},
            ],
        )

        # Only Skill 1's parameter-error retry should call the LLM; Skill 2 (pubmed)
        # must not inherit _script_name == 'run_code.py' and enter code self-correction.
        self.assertEqual(mock_llm.call.call_count, 1)
        self.assertEqual(results['tools_used'], ['pubmed'])
        self.assertEqual(len(results['papers']), 1)

    @patch('core.llm_client.get_llm_client')
    def test_run_code_runtime_self_correction_handles_none_new_params(self, mock_get_llm_client):
        self._write_skill_md('custom-runner', '# Custom Runner\n')

        mock_llm = MagicMock()
        mock_llm.call.return_value = 'import math\nprint(math.pi)\n'
        mock_get_llm_client.return_value = mock_llm

        self.inv.skill_registry.get_skill.return_value = {
            'name': 'custom-runner',
            'category': 'computation',
            'executables': ['/fake/skills/custom-runner/scripts/run_code.py'],
        }
        self.inv.skill_executor.execute_skill.side_effect = [
            {
                'status': 'success',
                'result': {
                    'return_code': 1,
                    'stderr': "ModuleNotFoundError: No module named 'broken_pkg'",
                },
            },
            {
                'status': 'success',
                'result': {
                    'return_code': 0,
                    'stderr': '',
                    'stdout': '3.14159',
                },
            },
        ]

        results = self.inv.run_tool_chain(
            topic='compute constant',
            pre_selected_skills=[
                {
                    'name': 'custom-runner',
                    'reason': 'evaluate expression',
                    'suggested_params': {'code': 'import broken_pkg\nprint(1)\n', 'query': 'compute constant'},
                }
            ],
        )

        self.assertEqual(mock_llm.call.call_count, 1)
        fix_prompt = mock_llm.call.call_args.kwargs['prompt']
        self.assertIn('import broken_pkg', fix_prompt)
        self.assertEqual(self.inv.skill_executor.execute_skill.call_count, 2)
        self.assertEqual(results['tools_used'], ['custom-runner'])


if __name__ == '__main__':
    unittest.main()
