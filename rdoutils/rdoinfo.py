
import os
import re

from distroinfo import info
from distroinfo import query
from rdopkg.utils import git
from rdopkg import helpers

local_info = os.environ['HOME'] + '/rdoinfo'
if not os.path.exists(local_info):
    os.makedirs(local_info)


def get_projects(tag=None, buildsys_tag=None):
    distroinfo = info.DistroInfo(
        info_files='rdo.yml',
        local_info=local_info)
    inforepo = distroinfo.get_info()

    all_packages = inforepo['packages']
    # If tag and buildys_tag are not specified it returns
    # all packages
    if tag is None and buildsys_tag is None:
        return all_packages
    pkgs_tagged = []
    # If tag is specified, it looks for packages with the specified
    # value in tags dict.
    if tag is not None:
        for package in all_packages:
            if tag in package['tags'].keys():
                pkgs_tagged.append(package)
    # If buildsys_tag is specified, it looks for packages with the specified
    # value in buildsys-tags dict.
    if buildsys_tag is not None:
        for package in all_packages:
            if ('buildsys-tags' in package.keys() and
                    buildsys_tag in package['buildsys-tags'].keys()):
                pkgs_tagged.append(package)
    return pkgs_tagged


def get_projects_distgit(tag=None, buildsys_tag=None):
    re_distgit = re.compile('.*?((puppet|openstack)/.*).git')
    projects = get_projects(tag=tag, buildsys_tag=buildsys_tag)
    distgits = []
    for project in projects:
        distgit_url = project['review-origin']
        # For some packages as dependencies, review-origin is None
        if distgit_url:
            distgit_short = re.search(re_distgit, distgit_url).group(1)
            distgits.append(distgit_short)
    return distgits


def get_pin(package, release):
    distroinfo = info.DistroInfo(
        info_files='rdo.yml',
        local_info=local_info)
    inforepo = distroinfo.get_info()
    pkgs = [p for p in inforepo['packages'] if p['name'] == package]
    if not pkgs or len(pkgs) != 1:
        raise NotInRdoinfo("Package %s not found in rdoinfo" % package)
    pkg = pkgs[0]
    if release in pkg['tags'].keys():
        pkg_rel_tag = pkg['tags'][release]
        if pkg_rel_tag and 'source-branch' in pkg_rel_tag.keys():
            return pkg_rel_tag['source-branch']
        else:
            return None
    else:
        raise NotInRdoinfoRelease("Package %s not found for release %s" %
                                  (package, release))


def get_new_pinned_builds(location, release):
    new_pins = []
    distroinfo = info.DistroInfo(
        info_files='rdo.yml',
        local_info=location)
    info2 = distroinfo.get_info()
    with helpers.cdir(location):
        with git.git_revision('HEAD~'):
            info1 = distroinfo.get_info()
    packages = query.tags_diff(info1, info2, tagsname='tags')
    for package in packages:
        name = package[0]
        tags = package[1]
        if release not in query.get_package(info1, name)['tags']:
            break
        pkg_tags = query.get_package(info2, name)['tags'][release]
        if release in tags and pkg_tags and 'source-branch' in pkg_tags.keys():
            pinned_version = pkg_tags['source-branch']
            new_pins.append({'name': name,
                             'release': release,
                             'version': pinned_version})
    return new_pins


class NotInRdoinfo(Exception):
    pass


class NotInRdoinfoRelease(Exception):
    pass
