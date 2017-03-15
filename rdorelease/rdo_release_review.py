import argparse
import datetime
import db
import os
import re
import rpm
import shutil

from rdopkg.actionmods import rdoinfo
from rdopkg.utils.cmd import git
from rdoutils import review_utils
from rdoutils import releases_utils
from rdoutils import rdoinfo as rdoinfo_utils
from sh import rdopkg
from sh import spectool

from db import Package
from utils import log_message
from utils import review_time_fmt


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
    return parser.parse_args()


def create_session(directory):
    db_path = "%s/reviews.sqlite" % datadir
    return db.get_session("sqlite:///%s" % db_path)


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
    session = create_session(directory)
    global user
    user = gerrit_user


def new_pkgs_review(review, inforepo):
    rel_date = review_time_fmt(review['submitted'])
    review_number = review['_number']
    log_message('INFO', "Processing releases for review %s" % review_number,
                logfile)
    new_pkgs = []
    new_releases = releases_utils.get_new_releases_review(review)
    for release in new_releases:
        for repo in release['repos']:
            log_message('INFO', "%s Found new repo version %s %s" % (
                        review_number, repo, release['version']), logfile)
            pkg = inforepo.find_package(repo, strict=True)
            if not pkg:
                # Some openstack packages are special and name in RDO !=
                # that repo name, i.e.: oslo.log vs oslo-log
                pkg = inforepo.find_package('git://git.openstack.org/%s' %
                                            repo, strict=True)
            if pkg:
                log_message('INFO', "%s Found new package %s %s" % (
                            review_number, pkg['name'], release['version']),
                            logfile)
                pkg = Package(
                    name=pkg['name'],
                    version=release['version'],
                    release_date=rel_date,
                    review_number=review_number,
                    osp_release=release['release'])
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


def new_version(package, version, release, dry_run=True):
    os.chdir("%s/%s" % (repodir, package))
    stable_branch = "%s-rdo" % release
    git('reset', '--hard', 'origin/%s' % stable_branch)
    git('checkout', stable_branch)
    cmd = ['new-version', '-b', '-U', version]
    if dry_run:
        cmd.append('-t')
        new_vers = rdopkg(*cmd)
    else:
        cmd.extend(['-p', 'review-patches/%s-rdo-patches' % release])
        new_vers = rdopkg(*cmd)
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
    except:
        return False


def process_package(package):
    log_message('INFO', "Processing package %s version %s for release %s" %
                (package.name, package.version, package.osp_release), logfile)
    try:
        rdoinfo_pin = rdoinfo_utils.get_pin(package.name, package.osp_release)
        if rdoinfo_pin and rdoinfo_pin != package.version:
            log_message('INFO', "Package %s pinned to version %s in rdoinfo" %
                        (package.name, rdoinfo_pin), logfile)
            return
        clone_distgit(package.name, package.osp_release)
        old_evr = get_evr(package.name)
        new_vers = new_version(package.name, package.version,
                               package.osp_release, dry_run=True)
        if new_vers_stderr(new_vers.stderr):
            log_message('INFO', new_vers_stderr(new_vers.stderr).group(1),
                        logfile)
        new_evr = get_evr(package.name)
        if not is_newer(new_evr, old_evr):
            log_message('INFO', "Version %s is not newer that existing %s" %
                        (new_evr, old_evr), logfile)
            db.update_status(session, package, 'NOT_REQUIRED')
            return
        if not tarball_exists(package.name):
            log_message('INFO', "Tarball for %s %s is not ready yet" %
                        (package.name, package.version), logfile)
            db.update_status(session, package, 'RETRY')
            return
        log_message('INFO', "Sending review for package %s version %s" %
                    (package.name, package.version), logfile)
        new_version(package.name, package.version, package.osp_release,
                    dry_run=False)
        db.update_status(session, package, 'CREATED')
    except NotBranchedPackage as e:
        log_message('ERROR', "Package %s %s for %s failed to build: %s" %
                    (package.name, package.version, package.osp_release,
                     e.message), logfile)
        db.update_status(session, package, 'NOTBRANCHED')
    except Exception as e:
        log_message('ERROR', "Package %s %s for %s failed to build: %s" %
                    (package.name, package.version, package.osp_release,
                     e.message), logfile)
        db.update_status(session, package, 'FAILED')


def process_packages(args):
    new_pkgs = db.get_packages(session, osp_release=args.release, status='NEW')
    failed_pkgs = db.get_packages(session, osp_release=args.release,
                                  status='FAILED')
    retry_pkgs = db.get_packages(session, osp_release=args.release,
                                 status='RETRY')
    pending_pkgs = new_pkgs + failed_pkgs + retry_pkgs
    for package in pending_pkgs:
        process_package(package)


def process_reviews(args):
    inforepo = rdoinfo.get_default_inforepo()
    inforepo.init(force_fetch=True)
    after = datetime.datetime.now() - datetime.timedelta(days=args.days)
    after_fmt = after.strftime('%Y-%m-%d')
    reviews = review_utils.get_osp_releases_reviews(args.release, after_fmt,
                                                    status='merged')
    for review in reviews:
        rev_num = review['_number']
        log_message('INFO', "Processing review %s" % rev_num, logfile)
        prev_review = db.get_reviews(session, review=rev_num)
        if not prev_review:
            new_pkgs = new_pkgs_review(review, inforepo)
            for new_pkg in new_pkgs:
                db.add_package(session, new_pkg)
            db.add_review(session, review, args.release)
            log_message('INFO', "Added review %s to database" % rev_num,
                        logfile)
        else:
            log_message('INFO', "Review %s already in database" % rev_num,
                        logfile)


def main():
    args = parse_args()
    env_prep(args.directory, args.user)
    process_reviews(args)
    process_packages(args)


class NotBranchedPackage(Exception):
    pass
