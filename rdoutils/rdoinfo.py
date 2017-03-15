
import os
import re

from rdopkg.actionmods import rdoinfo

local_info = os.environ['HOME'] + '/rdoinfo'
if not os.path.exists(local_info):
    os.makedirs(local_info)


def get_projects(tag=None):
    inforepo = rdoinfo.RdoinfoRepo(
        local_repo_path=local_info)
    inforepo.init(force_fetch=True)
    if tag is None:
        return inforepo.get_info()['packages']
    pkgs_release = []
    for package in inforepo.get_info()['packages']:
        if tag in package['tags'].keys():
            pkgs_release.append(package)
    return pkgs_release


def get_projects_distgit(tag=None):
    re_distgit = re.compile('.*?((puppet|openstack)/.*).git')
    projects = get_projects(tag=tag)
    distgits = []
    for project in projects:
        distgit_url = project['review-origin']
        distgit_short = re.search(re_distgit, distgit_url).group(1)
        distgits.append(distgit_short)
    return distgits


def get_pin(package, release):
    inforepo = rdoinfo.RdoinfoRepo(
        local_repo_path=local_info)
    inforepo.init(force_fetch=True)
    pkgs = [p for p in inforepo.get_info()['packages'] if p['name'] == package]
    if not pkgs or len(pkgs) != 1:
        raise KeyError("Package %s not found in rdoinfo" % package)
    pkg = pkgs[0]
    if release in pkg['tags'].keys():
        pkg_rel_tag = pkg['tags'][release]
        if pkg_rel_tag and 'source-branch' in pkg_rel_tag.keys():
            return pkg_rel_tag['source-branch']
        else:
            return None
    else:
        raise KeyError("Package %s not found for release %s" %
                       (package, release))
