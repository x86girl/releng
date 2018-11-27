
import os
import re
import ruamel.yaml as yaml

from distroinfo import info
from distroinfo import query
from rdopkg.utils import git
from rdopkg import helpers

local_info = os.environ['HOME'] + '/rdoinfo'
if not os.path.exists(local_info):
    os.makedirs(local_info)


def get_projects(info_files='rdo.yml', local_dir=local_info,
                 tag=None, buildsys_tag=None):
    distroinfo = info.DistroInfo(
        info_files=info_files,
        local_info=local_dir)
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


def get_project(project, info_files='rdo.yml', local_dir=local_info):
    all_packages = get_projects(info_files=info_files, local_dir=local_dir)
    for package in all_packages:
        if package['project'] == project:
            return package
    raise(NotInRdoinfo)


def update_tag(tag_type, project, tag_key, tag_value,
               info_files='rdo-full.yml', local_dir=local_info):
    """ Update tags or buildsys-tags in yaml files in rdoinfo with following
    convention:

        - file tags/foo.yaml contains values for tag 'foo'.
        - file buildsys-tags/bar.yaml contains values for buildsys-tag 'bar'.

    Usage examples:

        update_tag('tags', 'oslo-config',
                   'ocata', { 'source-branch': 3.22.2 },
                    local_dir='/tmp/rdoinfo')
        update_tag('buildsys-tags', 'oslo-config',
                   'cloud7-openstack-rocky-testing',
                   'python-oslo-config-6.4.0-1.el7',
                    local_dir='/tmp/rdoinfo')

    """
    package = get_project(project, info_files='rdo-full.yml',
                          local_dir=local_info)
    package[tag_type][tag_key] = tag_value
    # We update all tags for a given package to make sure we override
    # properly the default tags from package configs the first time
    # we update tags.
    for tag in package[tag_type].keys():
        updated = False
        tags_file = os.path.join(local_dir, tag_type, "%s.yml" % tag)
        with open(tags_file, 'rb') as infile:
            tags_info = yaml.load(infile, Loader=yaml.RoundTripLoader)
        # if packages section is empty we can't iterate.
        if tags_info['packages']:
            for pkg in tags_info['packages']:
                if pkg['project'] == project:
                    pkg[tag_type][tag] = package[tag_type][tag]
                    updated = True
        else:
            tags_info['packages'] = []
        # If the package does not exist in the release file, we have to
        # add it.
        if not updated:
            newpkg = {}
            newpkg['project'] = project
            newpkg[tag_type] = {tag: package[tag_type][tag]}
            tags_info['packages'].append(newpkg)
        tags_info['packages'].sort(key=lambda i: i['project'])
        with open(tags_file, 'w') as outfile:
            outfile.write(yaml.dump(tags_info, Dumper=yaml.RoundTripDumper,
                                    indent=2))


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
