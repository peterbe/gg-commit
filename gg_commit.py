import os
import time
import re
import getpass
import urllib


import git
import click

from gg.utils import error_out, get_repo, info_out
from gg.state import save, read
from gg.main import cli, pass_config
from gg.builtins import bugzilla
from gg.builtins import github


@cli.command()
@pass_config
def commit(config):
    """Commit the current branch."""
    try:
        repo = get_repo()
    except git.InvalidGitRepositoryError as exception:
        error_out('"{}" is not a git repository'.format(exception.args[0]))

    # untracked_files = repo.untracked_files
    # status = repo.index.diff(None)
    # untracked_files will list ALL files, even those inside sub-directories

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
    print("STATE", state)

        # print(path, age_friendly)
    # x.split(os.path.sep)[0] for x in untracked_files]
    # print(untracked_files)

    # if bugnumber:
    #     summary, bugnumber, url = get_summary(config, bugnumber)
    # else:
    #     url = None
    #     summary = None
    #
    # if summary:
    #     summary = input(
    #         'Summary ["{}"]: '.format(summary)
    #     ).strip() or summary
    # else:
    #     summary = input('Summary: ').strip()
    #
    # branch_name = ''
    # if bugnumber:
    #     branch_name = 'bug-{}-'.format(bugnumber)
    #
    # def clean_branch_name(string):
    #     string = re.sub('\s+', ' ', string)
    #     string = string.replace(' ', '-')
    #     string = string.replace('->', '-').replace('=>', '-')
    #     for each in '@%^&:\'"/(),[]{}!.?`$<>#*;=':
    #         string = string.replace(each, '')
    #     string = re.sub('-+', '-', string)
    #     return string.lower().strip()
    #
    # branch_name += clean_branch_name(summary)
    #
    # new_branch = repo.create_head(branch_name)
    # new_branch.checkout()
    # if config.verbose:
    #     click.echo('Checkout out new branch: {}'.format(branch_name))
    #
    # save(
    #     config.configfile,
    #     summary,
    #     branch_name,
    #     bugnumber=bugnumber,
    #     url=url,
    # )


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



def get_summary(config, bugnumber):
    """return a summary for this bug/issue. If it can't be found,
    return None."""

    bugzilla_url_regex = re.compile(
        re.escape('https://bugzilla.mozilla.org/show_bug.cgi?id=') + '(\d+)$'
    )

    # The user could have pasted in a bugzilla ID or a bugzilla URL
    if bugzilla_url_regex.search(bugnumber.split('#')[0]):
        # that's easy then!
        bugzilla_id, = bugzilla_url_regex.search(
            bugnumber.split('#')[0]
        ).groups()
        bugzilla_id = int(bugzilla_id)
        summary, url = bugzilla.get_summary(config, bugzilla_id)
        return summary, bugzilla_id, url

    # The user could have pasted in a GitHub issue URL
    github_url_regex = re.compile(
        'https://github.com/([^/]+)/([^/]+)/issues/(\d+)'
    )
    if github_url_regex.search(bugnumber.split('#')[0]):
        # that's also easy
        org, repo, id_, = github_url_regex.search(
            bugnumber.split('#')[0]
        ).groups()
        id_ = int(id_)
        title, url = github.get_title(
            config,
            org,
            repo,
            id_
        )
        return title, id_, url

    # If it's a number it can be either a github issue or a bugzilla bug
    if bugnumber.isdigit():
        # try both and see if one of them turns up something interesting

        repo = get_repo()
        state = read(config.configfile)
        fork_name = state.get('FORK_NAME', getpass.getuser())
        if config.verbose:
            info_out('Using fork name: {}'.format(fork_name))
        candidates = []
        # Looping over the remotes, let's figure out which one
        # is the one that has issues. Let's try every one that isn't
        # your fork remote.
        for origin in repo.remotes:
            if origin.name == fork_name:
                continue
            url = origin.url
            org, repo = parse_remote_url(origin.url)
            github_title, github_url = github.get_title(
                config,
                org,
                repo,
                int(bugnumber)
            )
            if github_title:
                candidates.append((
                    github_title,
                    int(bugnumber),
                    github_url,
                ))

        bugzilla_summary, bugzilla_url = bugzilla.get_summary(
            config,
            bugnumber
        )
        if bugzilla_summary:
            candidates.append((
                bugzilla_summary,
                int(bugnumber),
                bugzilla_url,
            ))

        if len(candidates) > 1:
            info_out(
                'Input is ambiguous. Multiple possibilities found. '
                'Please re-run with the full URL:'
            )
            for title, _, url in candidates:
                info_out('\t{}'.format(url))
                info_out('\t{}\n'.format(title))
            error_out('Awaiting your choice')
        elif len(candidates) == 1:
            return candidates[0]
        else:
            error_out('ID could not be found on GitHub or Bugzilla')
        raise Exception(bugnumber)

    return bugnumber, None, None


def parse_remote_url(url):
    """return a tuple of (org, repo) from the remote git URL"""
    # The URL will either be git@github.com:org/repo.git or
    # https://github.com/org/repo.git and in both cases
    # it's not guarantee that the domain is github.com.
    # FIXME: Make it work non-github.com domains
    if url.startswith('git@'):
        path = url.split(':', 1)[1]
    else:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path[1:]

    assert path.endswith('.git'), path
    path = path[:-4]
    return path.split('/')
