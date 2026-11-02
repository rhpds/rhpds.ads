"""Offline regression checks; requires PyYAML and ansible-core, no cluster."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


TASKS = Path(__file__).resolve().parents[1] / 'roles/ocp4_workload_trusted_software_factory/tasks/deploy_tsf.yml'


class DeploymentExitStatus(unittest.TestCase):
    def test_acceptance_requires_success_status_and_completion_marker(self):
        tasks = yaml.safe_load(TASKS.read_text())
        acceptance = next(t for t in tasks if t['name'] == 'Check TSF deployment status')
        cases = [({'rc': 0, 'stdout': 'Deployment complete!'}, True),
                 ({'rc': 42, 'stdout': 'Deployment complete!'}, False),
                 ({'rc': 0, 'stdout': 'pod test-tsf-tpa failed'}, False),
                 ({}, False)]
        with tempfile.TemporaryDirectory() as directory:
            for result, success in cases:
                with self.subTest(result=result):
                    play = [{'hosts': 'localhost', 'gather_facts': False, 'vars': {
                        'r_tsf_deploy': result,
                        'ocp4_workload_trusted_software_factory_namespace': 'tsf',
                        'ocp4_workload_trusted_software_factory_tpa_namespace': 'tsf-tpa',
                    }, 'tasks': [acceptance]}]
                    path = Path(directory) / 'acceptance.yml'
                    path.write_text(yaml.safe_dump(play))
                    env = dict(os.environ, ANSIBLE_LOCAL_TEMP=directory + '/ansible')
                    run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                          '-c', 'local', str(path)], capture_output=True, text=True, env=env)
                    self.assertEqual(run.returncode, 0 if success else 2, run.stdout + run.stderr)
                    self.assertIn('TSF deployment completed successfully' if success else
                                  'TSF deployment failed', run.stdout)

    def test_diagnostics_handle_missing_and_failed_pods_without_dumping_secrets(self):
        tasks = yaml.safe_load(TASKS.read_text())
        diagnostic = next(t for t in tasks if t['name'] == 'Display TSF deployment status')
        fixtures = [
            {'skipped': True},
            {'resources': []},
            {'resources': [{'status': {'phase': 'Failed', 'containerStatuses': [
                {'state': {'terminated': {'exitCode': 1, 'reason': 'Error', 'message': 'PRIVATE_SENTINEL'}}},
                {'state': {'waiting': {'reason': 'ImagePullBackOff', 'message': 'PRIVATE_SENTINEL'}}},
            ]}}]},
        ]
        plays = []
        for fixture in fixtures:
            plays.append({'hosts': 'localhost', 'gather_facts': False, 'vars': {
                'r_tsf_deploy': {'rc': 1, 'stdout': 'PRIVATE_SENTINEL'},
                'r_tsf_tpa_test': fixture,
            }, 'tasks': [diagnostic]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'diagnostics.yml'
            path.write_text(yaml.safe_dump(plays))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=directory + '/ansible')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                     '-c', 'local', str(path)], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('PRIVATE_SENTINEL', result.stdout)
            self.assertIn('ImagePullBackOff', result.stdout)

    def test_cli_exit_status_and_output_are_preserved(self):
        tasks = yaml.safe_load(TASKS.read_text())
        task = next(t for t in tasks if t['name'] == 'Deploy TSF via tsf CLI')
        command = task['kubernetes.core.k8s_exec']['command']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / 'tsf'
            cli.write_text('#!/bin/sh\necho deploy-output\necho deploy-error >&2\nexit "$TEST_EXIT"\n')
            cli.chmod(0o700)
            # Isolate the in-pod log path from the machine running the test.
            command = command.replace('/tmp/tsf-deploy.log', str(root / 'deploy.log'))
            for code in (0, 1, 42):
                with self.subTest(exit_code=code):
                    env = dict(os.environ, PATH=directory + os.pathsep + os.environ['PATH'], TEST_EXIT=str(code))
                    result = subprocess.run(command, shell=True, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, code)
                    self.assertIn('deploy-output', result.stdout)
                    self.assertIn('deploy-error', result.stdout)


if __name__ == '__main__':
    unittest.main()
