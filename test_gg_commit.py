import json
import os
import tempfile
import shutil

import git
import pytest
from click.testing import CliRunner

# By doing this import we make sure that the plugin is made available
# but the entry points loading inside gg.main.
# An alternative would we to set `PYTHONPATH=. py.test` (or something)
# but then that wouldn't test the entry point loading.
from gg.main import Config
from gg.testing import Response

from gg_commit import commit, humanize_seconds


@pytest.yield_fixture
def temp_configfile():
    tmp_dir = tempfile.mkdtemp('gg-start')
    fp = os.path.join(tmp_dir, 'state.json')
    with open(fp, 'w') as f:
        json.dump({}, f)
    yield fp
    shutil.rmtree(tmp_dir)


# def test_start(temp_configfile, mocker):
#     mocked_git = mocker.patch('git.Repo')
#     mocked_git().working_dir = 'gg-start-test'
#
#     runner = CliRunner()
#     config = Config()
#     config.configfile = temp_configfile
#     result = runner.invoke(start, [''], input='foo "bar"\n', obj=config)
#     assert result.exit_code == 0
#     assert not result.exception
#
#     mocked_git().create_head.assert_called_with('foo-bar')
#     mocked_git().create_head().checkout.assert_called_with()
#
#     with open(temp_configfile) as f:
#         saved = json.load(f)
#
#         assert 'gg-start-test:foo-bar' in saved
#         assert saved['gg-start-test:foo-bar']['description'] == 'foo "bar"'
#         assert saved['gg-start-test:foo-bar']['date']
#
#
# def test_start_weird_description(temp_configfile, mocker):
#     mocked_git = mocker.patch('git.Repo')
#     mocked_git().working_dir = 'gg-start-test'
#
#     runner = CliRunner()
#     config = Config()
#     config.configfile = temp_configfile
#     summary = "  a!@#$%^&*()_+{}[/]-= ;:   --> ==>  ---  `foo`   ,. <bar>     "
#     result = runner.invoke(start, [''], input=summary + '\n', obj=config)
#     assert result.exit_code == 0
#     assert not result.exception
#
#     expected_branchname = 'a_+-foo-bar'
#     mocked_git().create_head.assert_called_with(expected_branchname)
#     mocked_git().create_head().checkout.assert_called_with()
#
#     with open(temp_configfile) as f:
#         saved = json.load(f)
#
#         key = 'gg-start-test:' + expected_branchname
#         assert key in saved
#         assert saved[key]['description'] == summary.strip()
#
#
# def test_start_not_a_git_repo(temp_configfile, mocker):
#     mocked_git = mocker.patch('git.Repo')
#
#     mocked_git.side_effect = git.InvalidGitRepositoryError('/some/place')
#
#     runner = CliRunner()
#     config = Config()
#     config.configfile = temp_configfile
#     result = runner.invoke(start, [''], obj=config)
#     assert result.exit_code == 1
#     assert '"/some/place" is not a git repository' in result.output
#     assert 'Aborted!' in result.output
#     assert result.exception
#
#
# def test_start_a_digit(temp_configfile, mocker):
#     mocked_git = mocker.patch('git.Repo')
#     mocked_git().working_dir = 'gg-start-test'
#
#     remotes = []
#
#     class Remote:
#         def __init__(self, name, url):
#             self.name = name
#             self.url = url
#
#     remotes.append(Remote('origin', 'git@github.com:myorg/myrepo.git'))
#     remotes.append(Remote('other', 'https://github.com/o/ther.git'))
#     mocked_git().remotes.__iter__.return_value = remotes
#
#     rget = mocker.patch('requests.get')
#
#     def mocked_get(url, *args, **kwargs):
#         if url == 'https://bugzilla.mozilla.org/rest/bug/':
#             params = kwargs['params']
#             assert params['ids'] == '1234'
#             return Response({
#                 'bugs': [{
#                     'assigned_to': 'nobody@mozilla.org',
#                     'assigned_to_detail': {
#                         'email': 'nobody@mozilla.org',
#                         'id': 1,
#                         'name': 'nobody@mozilla.org',
#                         'real_name': 'Nobody; OK to take it and work on it'
#                     },
#                     'id': 1234,
#                     'status': 'NEW',
#                     'summary': 'This is the summary'
#                 }
#                 ],
#                 'faults': []
#             })
#         if url == 'https://api.github.com/repos/myorg/myrepo/issues/1234':
#             return Response({
#                 'id': 1234,
#                 'title': 'Issue Title Here',
#                 'html_url': (
#                     'https://api.github.com/repos/myorg/myrepo/issues/123'
#                 ),
#             })
#         if url == 'https://api.github.com/repos/o/ther/issues/1234':
#             return Response({'not': 'found'}, 404)
#         raise NotImplementedError(url)
#
#     rget.side_effect = mocked_get
#
#     runner = CliRunner()
#     config = Config()
#     config.configfile = temp_configfile
#     result = runner.invoke(start, ['1234'], obj=config)
#     assert 'Input is ambiguous' in result.output
#     assert 'Issue Title Here' in result.output
#     assert 'This is the summary' in result.output
#     assert result.exit_code == 1


def test_humanize_seconds():
    assert humanize_seconds(1) == '1 second'
    assert humanize_seconds(45) == '45 seconds'
    assert humanize_seconds(45 + 60) == '1 minute 45 seconds'
    assert humanize_seconds(45 + 60 * 2) == '2 minutes 45 seconds'
    assert humanize_seconds(60 * 60) == '1 hour'
    assert humanize_seconds(60 * 60 * 2) == '2 hours'
    assert humanize_seconds(60 * 60 * 24) == '1 day'
    assert humanize_seconds(60 * 60 * 24 * 2) == '2 days'
    assert humanize_seconds(60 * 60 * 24 * 7) == '1 week'
    assert humanize_seconds(60 * 60 * 24 * 14) == '2 weeks'
    assert humanize_seconds(60 * 60 * 24 * 28) == '1 month'
    assert humanize_seconds(60 * 60 * 24 * 28 * 2) == '2 months'
    assert humanize_seconds(60 * 60 * 24 * 28 * 12) == '1 year'
    assert humanize_seconds(60 * 60 * 24 * 28 * 12 * 2) == '2 years'
