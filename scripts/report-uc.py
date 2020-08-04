#!/usr/bin/python3
import argparse
import dnf
import koji
import pymod2pkg
import random
import requests
import rpm
import sys
import os
from tempfile import TemporaryDirectory
from re import search
from urllib.parse import urlparse

ARCH = 'x86_64'
DEFAULT_RELEASE = 'master'
DEFAULT_DISTRO = 'centos8'
DEFAULT_KOJI_PROFILE = 'cbs'
DEFAULT_PY_VERS = {'centos7': '2.7', 'centos8': '3.6',
                   'rhel7': '2.7', 'rhel8': '3.6'}
DISTROS = DEFAULT_PY_VERS.keys()
DNF_CACHEDIR = '/tmp/_report_uc_cache_dir'
UC = ('https://raw.githubusercontent.com/openstack/requirements/{}/'
      'upper-constraints.txt')

pkgs_base = None
tag_builds = {}


class UpperConstraint(object):

    def __init__(self, module_name, module_version, pkg_name, pkg_version,
                 source, release, status=None):
        self.module_name = module_name
        self.module_version = module_version
        self.pkg_name = pkg_name
        self.pkg_version = pkg_version
        self.source = source
        self.release = release
        self.status = self.vcmp(self.module_version, self.pkg_version)

    def vcmp(self, v1, v2=None):
        if not v2:
            return 'missing'
        t1 = ('0', v1, '')
        t2 = ('0', v2, '')
        c = rpm.labelCompare(t1, t2)
        if c == -1:
            return 'greater'
        elif c == 0:
            return 'equal'
        elif c == 1:
            return 'lower'

    def __str__(self):
        return ','.join([self.release, self.module_name, self.module_version,
                         self.pkg_name, self.pkg_version, self.source,
                         self.status])


def load_uc():
    """
    Load upper-constraints file directly from Github mirror.
    Returns a dictionary with a dictionary (module_name, module_version).
    """
    uc = {}
    if args.release != 'master':
        branch = 'stable/{}'.format(args.release)
    else:
        branch = args.release
    url = UC.format(branch)
    uc_file = requests.get(url)
    if uc_file.status_code == 404:
        print('The Openstack release "{}" does not exist.'.format(
            args.release))
        sys.exit(1)
    elif uc_file.status_code != 200:
        print('Could not download upper-constraints file from {}'.format(url))
        sys.exit(1)

    for line in uc_file.text.split('\n'):
        m = search(r'^(.*)===([\d\.]+)(;python_version==\'(.*)\')?', line)
        if not m:
            continue
        name, version, py_vers = m.group(1), m.group(2), m.group(4)
        # we skip it if the python_version does not match the distro's one
        if py_vers is not None and py_vers != DEFAULT_PY_VERS[args.distro]:
            continue
        uc[name] = version
    return uc


def is_url(url):
    try:
        result = urlparse(url)
        if result.scheme not in ['http', 'https']:
            return False
        if all([result.scheme, result.netloc]):
            return True
        else:
            return False
    except Exception:
        return False


def download_repo_from_url(url, dest_dir):
    """
    Download .repo file from an URL
    The filenames need to be randomized to avoid files to be
    overwritten on FS.
    """
    if not is_url(url):
        print("'{}' is probably not a valid URL.".format(url))
        sys.exit(1)

    file_name = random.getrandbits(128)
    local_repo_file = '{}/{}.repo'.format(dest_dir, file_name)

    remote_file = requests.get(url)
    if remote_file.status_code == 404:
        print('The .repo file does not exist at: {}'.format(url))
        sys.exit(1)
    elif remote_file.status_code != 200:
        print('Could not download the .repo file from {}'.format(url))
        sys.exit(1)

    r = requests.get(url)
    with open(local_repo_file, 'wb') as output_file:
        output_file.write(r.content)
        return local_repo_file


def add_repo_from_url_in_repos_dir():
    """
    Add .repo files from URL in repos_dir directory.
    Return a list of the downloaded file paths that need to be removed from
    filesystem after being add to dnf.Base.
    """
    local_repo_files = []
    for _repo_url in args.repo_url:
        local_repo = download_repo_from_url(_repo_url, args.repos_dir)
        local_repo_files.append(local_repo)
    return local_repo_files


def remove_files(files_list):
    for _f in files_list:
        try:
            os.remove(_f)
        except OSError:
            print("Could not remove file {}".format(_f))


def create_dir(path):
    """
    Create a directory, do nothing if already exists."""
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    except OSError as e:
        print("Could not create directory: {}".format(e))
        sys.exit(1)


def dnf_base(distro):
    """
    Instanciate a DNF.base for the distro passed as argument, and
    configure it.
    """
    distro_name, distro_rel_ver = distro[:-1], distro[-1]
    base = dnf.Base()
    conf = base.conf
    create_dir(DNF_CACHEDIR)
    conf.cachedir = DNF_CACHEDIR
    conf.substitutions['releasever'] = distro_rel_ver
    conf.substitutions['basearch'] = ARCH
    if distro_name == 'centos':
        conf.substitutions['contentdir'] = distro_name
    conf.reposdir = args.repos_dir
    conf.config_file_path = ''
    return base


def add_repos_to_base(base):
    """
    Add repos  passed as arguments (repoid,baseurl) in the 'base' object.
    """
    repo_id, base_url = '', ''
    for _repo in args.repo:
        try:
            repo_id, base_url = _repo.split(',')
        except ValueError:
            print("Could not add repo: {}".format(_repo))
            sys.exit(1)
        base.repos.add_new_repo(repo_id, base.conf, baseurl=[base_url])


def download_repos_metadata():
    """
    Load information about packages from the enabled repositories into
    the sack.
    """
    global pkgs_base
    if pkgs_base:
        return pkgs_base
    pkgs_base = dnf_base(args.distro)
    add_repos_to_base(pkgs_base)
    local_repo_url_files = add_repo_from_url_in_repos_dir()
    pkgs_base.read_all_repos()
    remove_files(local_repo_url_files)
    pkgs_base.fill_sack(load_system_repo=False)


def repoquery(*args, **kwargs):
    """
    A Python function that somehow works as the repoquery command.
    Only supports --provides and --all.
    """
    download_repos_metadata()
    if 'provides' in kwargs:
        return pkgs_base.sack.query().filter(provides=kwargs['provides']).run()
    if 'all' in kwargs and kwargs['all']:
        return pkgs_base.sack.query()
    raise RuntimeError('unknown query')


def get_packages_provided_by_repos(mod_name, mod_version, provided_uc):
    """
    Find packages that provide the module.
    For distro with releasever > 7, we take advantage of the Python
    dependency generator (e.g python3dist(foo)) which returns the package name.
    Else, we use pymod2pkg to get package names.
    After, the repoquery command execution, we append the global list with the
    result.
    """
    if int(args.distro[-1]) > 7:
        pkg_name = "python3dist({})".format(mod_name.lower())
    else:
        pkg_name = pymod2pkg.module2package(mod_name, 'fedora')
    provides = repoquery(provides=pkg_name)
    if len(provides) > 0:
        for pkg in provides:
            provided_uc.append(UpperConstraint(mod_name, mod_version,
                                               pkg.name,
                                               pkg.version,
                                               pkg.reponame,
                                               args.release))
    else:
        provided_uc.append(UpperConstraint(mod_name, mod_version,
                                           '',
                                           '',
                                           '',
                                           args.release))


def list_builds_from_tag(tag):
    """
    Get builds from a Koji tag passed as argument.
    A Koji profile can also be passed as argument.
    Returns a dictionary (build name, (version, tag))
    """
    builds = {}
    try:
        koji_module = koji.get_profile_module(args.koji_profile)
    except Exception as e:
        print('Error: could not load the koji profile ({})'.format(e))
        sys.exit(1)
    client = koji_module.ClientSession(koji_module.config.server)
    try:
        for _b in client.listTagged(tag):
            builds[_b['name']] = {'version': _b['version'],
                                  'tag': _b['tag_name']}
    except Exception as e:
        print('Error: could not list builds ({})'.format(e))
        sys.exit(1)
    tag_builds[tag] = builds
    return builds


def get_builds_by_koji_tag(tag, mod_name, mod_version, provided_uc):
    """
    Find builds that provide the module.
    """
    try:
        builds = tag_builds[tag]
    except KeyError:
        builds = list_builds_from_tag(tag)
    pkg_name = pymod2pkg.module2package(mod_name, 'fedora')
    try:
        builds[pkg_name]
        provided_uc.append(UpperConstraint(mod_name, mod_version,
                                           pkg_name,
                                           builds[pkg_name]['version'],
                                           builds[pkg_name]['tag'],
                                           args.release))
    except KeyError:
        provided_uc.append(UpperConstraint(mod_name, mod_version,
                                           '',
                                           '',
                                           tag,
                                           args.release))


def provides_uc():
    provided_uc = []
    uc = load_uc()
    if args.repo_url and args.repos_dir is None:
        td = TemporaryDirectory()
        args.repos_dir = td.name

    for mod_name, mod_version in uc.items():
        if args.repo or args.repos_dir or args.repo_url:
            get_packages_provided_by_repos(mod_name, mod_version, provided_uc)
        if args.tag:
            get_builds_by_koji_tag(args.tag, mod_name, mod_version,
                                   provided_uc)
        if not args.repo and not args.repos_dir and not args.repo_url \
                and not args.tag:
            print('Please provide at least one repo or koji tag.')
            sys.exit(1)
    return provided_uc


def print_source_informations(nbr_of_matches_from_source):
    print("\nEnabled repositories/tag:")
    if pkgs_base is not None and pkgs_base.repos:
        for repo in pkgs_base.repos.iter_enabled():
            try:
                number_of_pkgs = nbr_of_matches_from_source[repo.id]
            except KeyError:
                number_of_pkgs = 0
            print("- repoid: {}".format(repo.id))
            print("  number: {}".format(number_of_pkgs))
            print("  baseurl: {}".format(repo.baseurl[0]))
    if args.tag:
        try:
            number_of_pkgs = nbr_of_matches_from_source[args.tag]
        except KeyError:
            number_of_pkgs = 0
        print("- tag: {}".format(args.tag))
        print("  number: {}".format(number_of_pkgs))
        print("  koji_profile: {}".format(args.koji_profile))


def increment_counter(source, counter):
    """Increment the number of matches from a repo/tag source."""
    try:
        counter[source] += 1
    except KeyError:
        counter.update({source: 1})


def main():
    nbr_of_matches_from_source = {}
    for uc in provides_uc():
        if args.status == '' or \
                (args.status != '' and uc.status == args.status):
            print(uc)
            if args.verbose:
                increment_counter(uc.source, nbr_of_matches_from_source)
    if args.verbose:
        print_source_informations(nbr_of_matches_from_source)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=("Compare upper-constraints "
                                                  "with existing repos/tags."))
    parser.add_argument('-o', '--release',
                        required=True,
                        default=DEFAULT_RELEASE,
                        help=('openstack release (i.e. [{}], ussuri, train '
                              ', etc)'.format(DEFAULT_RELEASE)))
    parser.add_argument('-d', '--distro',
                        choices=DISTROS,
                        default=DEFAULT_DISTRO,
                        help='distribution name (default {})'.format(
                            DEFAULT_DISTRO))
    parser.add_argument('-k', '--koji-profile',
                        default=DEFAULT_KOJI_PROFILE,
                        help='koji profile to load (default: {})'.format(
                            DEFAULT_KOJI_PROFILE))
    parser.add_argument('-r', '--repo', action='append', default=[],
                        help="add repo (i.e repoid,baseurl)")
    parser.add_argument('--repo-url', action='append', default=[],
                        help="add a .repo file from an URL")
    parser.add_argument('-R', '--repos-dir',
                        help="directory containing repo files")
    parser.add_argument('-s', '--status',
                        choices=['lower', 'equal', 'greater', 'missing'],
                        default='',
                        help=("filter on status (i.e lower, equal, greater, "
                              "missing)"))
    parser.add_argument('-t', '--tag',
                        default='',
                        help=('get builds from a koji tag '
                              '(i.e cloud8-openstack-ussuri-release)'))
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=False,
                        help='verbose mode')
    args = parser.parse_args()

    main()
