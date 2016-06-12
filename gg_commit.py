# -*- coding: utf-8 -*-

import os
import time
import re
import getpass
import urllib


import git
import click

from gg.utils import error_out, get_repo, info_out, get_repo_name
from gg.state import save, read
from gg.main import cli, pass_config
from gg.builtins import bugzilla
from gg.builtins import github


@cli.command()
@click.option(
    '-n', '--no-verify',
    default=False,
    help="This option bypasses the pre-commit and commit-msg hooks."
)
@pass_config
def commit(config, no_verify):
    """Commit the current branch."""
    try:
        repo = get_repo()
    except git.InvalidGitRepositoryError as exception:
        error_out('"{}" is not a git repository'.format(exception.args[0]))

    # untracked_files = repo.untracked_files
    # status = repo.index.diff(None)
    # untracked_files will list ALL files, even those inside sub-directories
    # print(repo.head)
    # print(dir(repo))
    # print(type(repo.head))
    # print(repr(repo.head.name))

    active_branch = repo.active_branch
    # print(repr(active_branch.name))
    if active_branch.name == 'master':
        error_out(
            "Can't commit when on the master branch. "
            "You really ought to do work in branches."
        )
    untracked_files = {}
    now = time.time()

    for path in repo.untracked_files:
        age = now - os.stat(path).st_mtime
        # age_friendly = human_seconds(age)
        root = path.split(os.path.sep)[0]
        if root in untracked_files:
            if age < untracked_files[root]:
                # youngest file in that directory
                untracked_files[root] = age
        else:
            untracked_files[root] = age

    if untracked_files:
        ordered = sorted(
            untracked_files.items(),
            key=lambda x: x[1],
            reverse=True
        )
        print("NOTE! There are untracked files:")
        for path, age in ordered:
            if os.path.isdir(path):
                path = path + '/'
            print("\t", path.ljust(60), humanize_seconds(age))

        # But only put up this input question if one the files is
        # younger than 12 hours.
        young_ones = [x for x in untracked_files.values() if x < 60 * 60 * 12]
        if young_ones:
            ignore = input("Ignore untracked files? [Y/n] ").lower().strip()
            if ignore.lower().strip() == 'n':
                error_out(
                    "\n\tLeaving it up to you to figure out what to do "
                    "with those untracked files."
                )
                return 1
            print("")

    state = read(config.configfile)
    # state = load()
    # this_repo_name = get_repo_name()

    # Replace this with gg.state.load(configfile, active_branch.name) XXX
    key = '{}:{}'.format(get_repo_name(), active_branch.name)
    try:
        data = state[key]
    except KeyError:
        error_out(
            "You're in a branch that was not created with gg.\n"
            "No branch information available."
        )

    from pprint import pprint
    # print("STATE", state)
    # pprint(state)
    # print('-')
    # pprint(data)
    # print("DATA", data)

    if data.get('bugnumber'):
        msg = 'bug {} - {}'.format(data['bugnumber'], data['description'])
    else:
        msg = data['description']

    print('Commit message:')
    print('\t', msg)
    print('')

    confirm = input('OK? [Y/n] ').lower().strip()
    if confirm in ('n', 'no'):
        try_again = input(
            'Type a new commit message (or empty to exit): '
        ).strip()
        if not try_again:
            error_out('Commit cancelled')
        msg = try_again

    if data['bugnumber']:  # XXX need to distinguish between bugzilla and github
        fixes = input(
            'Add the "fixes" prefix? [N/y] '
        ).lower().strip()
        if fixes in ('y', 'yes'):
            msg = 'fixes ' + msg

    # Now we're going to do the equivalent of `git commit -a -m "..."`
    index = repo.index
    # add every file
    files = [path for path, stage in repo.index.entries.keys()]
    if not files:
        error_out("No files to add")
    print(files)
    if not repo.is_dirty():
        error_out("Branch is not dirty. There is nothing to commit.")
    # error_out('test')
    index.add(files)
    try:
        commit = index.commit(msg)
    except git.exc.HookExecutionError as exception:
        if not no_verify:
            info_out('Commit hook failed ({}, exit code {})'.format(
                exception.command,
                exception.status,
            ))
            if exception.stdout:
                error_out(exception.stdout)
            elif exception.stderr:
                error_out(exception.stderr)
            else:
                error_out('Commit hook failed.')
        else:
            raise NotImplementedError(
                "Need to commit without executing the commit hooks"
            )

    if config.verbose:
        print("COMMIT", repr(commit))
        print(dir(commit))
        # XXX
        success_out('Need to say something about the commit')

    if not state.get('FORK_NAME'):
        info_out(
            "Can't help you push the commit. Please run: gg config --help"
        )
        return 0

    try:
        repo.remotes[state['FORK_NAME']]
    except IndexError:
        error_out(
            "There is no remote called '{}'".format(state['FORK_NAME'])
        )

    push_for_you = input(
        'Push branch to {}? [Y/n] '.format(state['FORK_NAME'])
    ).lower().strip()
    if push_for_you not in ('n', 'no'):
        destination = repo.remotes[state['FORK_NAME']]
        destination.push()

    if not state.get('GITHUB'):
        if config.verbose:
            info_out(
                "Can't help create a GitHub Pull Request.\n"
                "Consider running: gg github --help"
            )
        return 0

    origin = repo.remotes[state.get('ORIGIN_NAME', 'origin')]
    rest = re.split('github\.com[:/]', origin.url)[1]
    org, repo = rest.split('.git')[0].split('/', 1)

    github_url = 'https://github.com/{}/{}/compare/{}:{}...{}:{}?expand=1'
    github_url = github_url.format(
        org,
        repo,
        org,
        'master',
        state['FORK_NAME'],
        active_branch.name
    )
    print("Now, to make a Pull Request, go to:")
    print("")
    print(url)
    print("(⌘-click to open URLs)")

    return 0


def _humanize_time(amount, units):
    """Chopped and changed from http://stackoverflow.com/a/6574789/205832"""
    intervals = (
        1,
        60,
        60 * 60,
        60 * 60 * 24,
        604800,
        2419200,
        29030400
    )
    names = (
        ('second', 'seconds'),
        ('minute', 'minutes'),
        ('hour', 'hours'),
        ('day', 'days'),
        ('week', 'weeks'),
        ('month', 'months'),
        ('year', 'years'),
    )

    result = []
    unit = [x[1] for x in names].index(units)
    # Convert to seconds
    amount = amount * intervals[unit]
    for i in range(len(names)-1, -1, -1):
        a = int(amount) // intervals[i]
        if a > 0:
            result.append((a, names[i][1 % a]))
            amount -= a * intervals[i]
    return result

def humanize_seconds(seconds):
    parts = [
        '{} {}'.format(x, y)
        for x, y in _humanize_time(seconds, 'seconds')
    ]
    return ' '.join(parts)



# def get_summary(config, bugnumber):
#     """return a summary for this bug/issue. If it can't be found,
#     return None."""
#
#     bugzilla_url_regex = re.compile(
#         re.escape('https://bugzilla.mozilla.org/show_bug.cgi?id=') + '(\d+)$'
#     )
#
#     # The user could have pasted in a bugzilla ID or a bugzilla URL
#     if bugzilla_url_regex.search(bugnumber.split('#')[0]):
#         # that's easy then!
#         bugzilla_id, = bugzilla_url_regex.search(
#             bugnumber.split('#')[0]
#         ).groups()
#         bugzilla_id = int(bugzilla_id)
#         summary, url = bugzilla.get_summary(config, bugzilla_id)
#         return summary, bugzilla_id, url
#
#     # The user could have pasted in a GitHub issue URL
#     github_url_regex = re.compile(
#         'https://github.com/([^/]+)/([^/]+)/issues/(\d+)'
#     )
#     if github_url_regex.search(bugnumber.split('#')[0]):
#         # that's also easy
#         org, repo, id_, = github_url_regex.search(
#             bugnumber.split('#')[0]
#         ).groups()
#         id_ = int(id_)
#         title, url = github.get_title(
#             config,
#             org,
#             repo,
#             id_
#         )
#         return title, id_, url
#
#     # If it's a number it can be either a github issue or a bugzilla bug
#     if bugnumber.isdigit():
#         # try both and see if one of them turns up something interesting
#
#         repo = get_repo()
#         state = read(config.configfile)
#         fork_name = state.get('FORK_NAME', getpass.getuser())
#         if config.verbose:
#             info_out('Using fork name: {}'.format(fork_name))
#         candidates = []
#         # Looping over the remotes, let's figure out which one
#         # is the one that has issues. Let's try every one that isn't
#         # your fork remote.
#         for origin in repo.remotes:
#             if origin.name == fork_name:
#                 continue
#             url = origin.url
#             org, repo = parse_remote_url(origin.url)
#             github_title, github_url = github.get_title(
#                 config,
#                 org,
#                 repo,
#                 int(bugnumber)
#             )
#             if github_title:
#                 candidates.append((
#                     github_title,
#                     int(bugnumber),
#                     github_url,
#                 ))
#
#         bugzilla_summary, bugzilla_url = bugzilla.get_summary(
#             config,
#             bugnumber
#         )
#         if bugzilla_summary:
#             candidates.append((
#                 bugzilla_summary,
#                 int(bugnumber),
#                 bugzilla_url,
#             ))
#
#         if len(candidates) > 1:
#             info_out(
#                 'Input is ambiguous. Multiple possibilities found. '
#                 'Please re-run with the full URL:'
#             )
#             for title, _, url in candidates:
#                 info_out('\t{}'.format(url))
#                 info_out('\t{}\n'.format(title))
#             error_out('Awaiting your choice')
#         elif len(candidates) == 1:
#             return candidates[0]
#         else:
#             error_out('ID could not be found on GitHub or Bugzilla')
#         raise Exception(bugnumber)
#
#     return bugnumber, None, None
#
#
# def parse_remote_url(url):
#     """return a tuple of (org, repo) from the remote git URL"""
#     # The URL will either be git@github.com:org/repo.git or
#     # https://github.com/org/repo.git and in both cases
#     # it's not guarantee that the domain is github.com.
#     # FIXME: Make it work non-github.com domains
#     if url.startswith('git@'):
#         path = url.split(':', 1)[1]
#     else:
#         parsed = urllib.parse.urlparse(url)
#         path = parsed.path[1:]
#
#     assert path.endswith('.git'), path
#     path = path[:-4]
#     return path.split('/')
