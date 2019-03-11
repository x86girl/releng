import argparse
import datetime
import os
import re
import rpm
import shutil
import time

from distroinfo import info
from distroinfo import query
from rdopkg.utils.git import git
from rdoutils import review_utils
from rdoutils import releases_utils
from rdoutils import rdoinfo as rdoinfo_utils
from rdoutils.rdoinfo import NotInRdoinfoRelease
from sh import rdopkg
from sh import spectool

from utils import log_message

rdoinfo_repo = ('https://raw.githubusercontent.com/'
                'redhat-openstack/rdoinfo/master/')


def parse_args():
    parser = argparse.ArgumentParser(description='Process information about \
                                     reviews on openstack/releases project')
    parser.add_argument('-r', '--release', dest='release',
                        help='OpenStack release')
    parser.add_argument('-d', '--days', dest='days', default=1, type=int,
                        help='Number of days to process')
    parser.add_argument('-b', '--directory', dest='directory',
                        default=os.environ['HOME'],
                        help='Base directory for aplication')
    parser.add_argument('-u', '--user', dest='user',
                        default=os.environ['USER'],
                        help='Base directory for aplication')
    parser.add_argument('--dry-run', dest='dry_run',
                        action='store_true', default=False,
                        help='Run in dry-run mode, do not send the review')
    parser.add_argument('-n', '--review-number', dest='number',
                        default=None,
                        help='Review number to process, can also use '
                        'commit:<commit hash> or change:<change-id> for strict'
                        ' search for commit hash or change-id respectively')
    parser.add_argument('-p', '--rdoinfo-pins', dest='rdoinfo_pins',
                        default=None,
                        help='Path to rdoinfo when creating new releases from'
                        'rdoinfo pin updates instead of releases reviews')
    parser.add_argument('-e', '--changelog-email', dest='changelog_email',
                        default=None,
                        help='Email address to use in changelog entry for'
                        'the new release')
    parser.add_argument('-c', '--changelog-user', dest='changelog_user',
                        default=None,
                        help='User name to include in changelog entry for'
                        'the new release')
    parser.add_argument('-t', '--rdoinfo-tag', dest='rdoinfo_tag',
                        default=None,
                        help='Tag in rdoinfo associated with this release.'
                        'By default the release name')
    return parser.parse_args()


def create_dirs(directory):
    log_message('INFO', "Running rdo_auto_release in %s directory" % directory,
                logfile, stdout_only=True)
    dir_list = [directory, datadir, logdir, repodir]
    for directory in dir_list:
        if not os.path.exists(directory):
            os.makedirs(directory)


def env_prep(directory, gerrit_user):
    global datadir
    datadir = directory + '/data'
    global logdir
    logdir = directory + '/logs/'
    global logfile
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    logfile = "%s%s-rdo-auto-release.log" % (logdir, now)
    global repodir
    repodir = datadir + '/distgits'
    create_dirs(directory)
    global session
    global user
    user = gerrit_user
    # We need to force TERM variables to invoke rdopkg methods
    # from library. In some cases as cron or jenkins it's not set
    # in environment
    os.environ["TERM"] = "linux"
    os.environ["TERMINFO"] = '/etc/terminfo'


def new_pkgs_review(review, inforepo):
    review_number = review['_number']
    log_message('INFO', "Processing releases for review %s" % review_number,
                logfile)
    new_pkgs = []
    new_releases = releases_utils.get_new_releases_review(review)
    for release in new_releases:
        for repo in release['repos']:
            log_message('INFO', "%s Found new repo version %s %s" % (
                        review_number, repo, release['version']), logfile)
            pkg = query.find_package(inforepo, repo, strict=True)
            if not pkg:
                # Some openstack packages are special and name in RDO !=
                # that repo name, i.e.: oslo.log vs oslo-log
                repo_url = 'git://git.openstack.org/%s' % repo
                pkg = query.find_package(inforepo, repo_url, strict=True)
            if pkg:
                log_message('INFO', "%s Found new package %s %s" % (
                            review_number, pkg['name'], release['version']),
                            logfile)
                pkg = {'name': pkg['name'],
                       'version': release['version'],
                       'osp_release': release['release']}
                new_pkgs.append(pkg)
    return new_pkgs


def get_evr(package):
    os.chdir("%s/%s" % (repodir, package))
    tran = rpm.TransactionSet()
    spec = tran.parseSpec('%s.spec' % package)
    hdr = spec.packages[0].header
    e = hdr.format('%{epoch}')
    v = hdr.format('%{version}')
    r = hdr.format('%{release}')
    return (e, v, r)


def clone_distgit(package, release):
    os.chdir(repodir)
    if os.path.exists(package):
        shutil.rmtree(package)
    rdopkg('clone', package, '-u', user)
    os.chdir(package)
    stable_branch = "%s-rdo" % release
    exist_remote = git.ref_exists('refs/remotes/origin/%s' % stable_branch)
    if exist_remote:
        git.create_branch(stable_branch, "origin/%s" % stable_branch)
        git('checkout', stable_branch)
    else:
        raise NotBranchedPackage("Distgit for %s does not contain branch %s" %
                                 (package, stable_branch))


def new_version(package, version, release, dry_run=True,
                chglog_user=None, chglog_email=None):
    os.chdir("%s/%s" % (repodir, package))
    stable_branch = "%s-rdo" % release
    git('reset', '--hard', 'origin/%s' % stable_branch)
    git('checkout', stable_branch)
    cmd = ['new-version', '-b', '-U', version, '-t']
    if chglog_user:
        cmd = cmd + ['-u', chglog_user]
    if chglog_email:
        cmd = cmd + ['-e', chglog_email]
    new_vers = rdopkg(*cmd)
    if not dry_run:
        git('review', '-t', '%s-update' % release)
    return new_vers


def new_vers_stderr(msg):
    stderr_re = re.compile(".*(package is already at version.*)")
    return stderr_re.search(msg)


def is_newer(new_evr, old_evr):
    comp = rpm.labelCompare(new_evr, old_evr)
    return comp == 1


def tarball_exists(package):
    os.chdir("%s/%s" % (repodir, package))
    try:
        spectool('-g', "%s.spec" % package)
        return True
    except Exception:
        return False


def wait_for_tarball(package, retries=40, wait=30):
    retry = 0
    while retry < retries:
        tarball_exist = tarball_exists(package)
        if tarball_exist:
            return True
        else:
            # Wait for sometime before retrying
            time.sleep(wait)
        retry += 1
    return False


def is_release_tag(package, version):
    os.chdir("%s/%s" % (repodir, package))
    is_tag = git.ref_exists('refs/tags/%s' % version)
    return is_tag


def process_package(name, version, osp_release, dry_run, check_tag=False,
                    check_tarball=False, chglog_user=None, chglog_email=None,
                    rdoinfo_tag=None):
    log_message('INFO', "Processing package %s version %s for release %s" %
                (name, version, osp_release), logfile)
    if rdoinfo_tag is None:
        rdoinfo_tag = osp_release
    try:
        rdoinfo_pin = rdoinfo_utils.get_pin(name, rdoinfo_tag)
        if rdoinfo_pin and rdoinfo_pin != version:
            log_message('INFO', "Package %s pinned to version %s in rdoinfo" %
                        (name, rdoinfo_pin), logfile)
            return
        clone_distgit(name, osp_release)
        if check_tag and not is_release_tag(name, version):
            log_message('INFO', "Package %s has not release tag %s" %
                        (name, version), logfile)
            return
        old_evr = get_evr(name)
        new_vers = new_version(name, version, osp_release, dry_run=True,
                               chglog_user=chglog_user,
                               chglog_email=chglog_email)
        if new_vers_stderr(new_vers.stderr):
            log_message('INFO', new_vers_stderr(new_vers.stderr).group(1),
                        logfile)
        new_evr = get_evr(name)
        if not is_newer(new_evr, old_evr):
            log_message('INFO', "Version %s is not newer that existing %s" %
                        (new_evr, old_evr), logfile)
            return
        if check_tarball and not wait_for_tarball(name):
            tag_exists = is_release_tag(name, version)
            log_message('INFO', "Tarball for %s %s is not ready yet, "
                        "Tag exists: %s" %
                        (name, version, tag_exists), logfile)
        log_message('INFO', "Sending review for package %s version %s" %
                    (name, version), logfile)
        new_version(name, version, osp_release, dry_run=dry_run,
                    chglog_user=chglog_user, chglog_email=chglog_email)
        if dry_run:
            log_message('INFO', "Running in dry-run mode. Review is not sent",
                        logfile)
    except NotBranchedPackage as e:
        log_message('INFO', "Package %s %s for %s is not required: %s" %
                    (name, version, osp_release, e.message), logfile)
    except NotInRdoinfoRelease as e:
        log_message('INFO', "Package %s is not in release %s" % (name,
                    osp_release), logfile)
    except Exception as e:
        log_message('ERROR', "Package %s %s for %s failed to build: %s" %
                    (name, version, osp_release, e.message), logfile)
        raise e


def process_reviews(args):
    distroinfo = info.DistroInfo(
        info_files='rdo.yml',
        remote_info=rdoinfo_repo)
    inforepo = distroinfo.get_info()
    if args.number:
        after_fmt = None
    else:
        after = datetime.datetime.now() - datetime.timedelta(days=args.days)
        after_fmt = after.strftime('%Y-%m-%d')
    reviews = review_utils.get_osp_releases_reviews(args.release,
                                                    after=after_fmt,
                                                    number=args.number,
                                                    status='merged')
    for review in reviews:
        rev_num = review['_number']
        log_message('INFO', "Processing review %s" % rev_num, logfile)
        new_pkgs = new_pkgs_review(review, inforepo)
        for new_pkg in new_pkgs:
            if new_pkg['osp_release'] == args.release:
                process_package(new_pkg['name'], new_pkg['version'],
                                new_pkg['osp_release'], args.dry_run,
                                check_tarball=True,
                                chglog_user=args.changelog_user,
                                chglog_email=args.changelog_email,
                                rdoinfo_tag=args.rdoinfo_tag)


def process_rdoinfo(args):
    if args.rdoinfo_tag is None:
        rdoinfo_tag = args.release
    else:
        rdoinfo_tag = args.rdoinfo_tag
    new_pins = rdoinfo_utils.get_new_pinned_builds(args.rdoinfo_pins,
                                                   rdoinfo_tag)
    for pin in new_pins:
        log_message('INFO', "rdoinfo Found new package %s %s %s" % (
                    pin['name'], pin['version'], pin['release']), logfile)
        process_package(pin['name'], pin['version'], args.release,
                        args.dry_run, check_tag=True,
                        chglog_user=args.changelog_user,
                        chglog_email=args.changelog_email,
                        rdoinfo_tag=rdoinfo_tag)


def main():
    args = parse_args()
    env_prep(args.directory, args.user)
    if args.rdoinfo_pins:
        process_rdoinfo(args)
    else:
        process_reviews(args)


class NotBranchedPackage(Exception):
    pass
