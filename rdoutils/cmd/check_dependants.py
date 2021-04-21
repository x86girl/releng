#! /usr/bin/python3
#
# Mostly copied code from find_unblocked_orphans.py in fedora
#
# Credits to original authors:
#     Jesse Keating <jkeating@redhat.com>
#     Till Maas <opensource@till.name>
#
# Copyright (c) 2009-2013 Red Hat
# SPDX-License-Identifier: GPL-2.0
#
# From:
# https://pagure.io/releng/blob/main/f/scripts/find_unblocked_orphans.py

from collections import OrderedDict
import argparse
import os
import sys

import dnf


def get_repos(release):
    RDO_TRUNK_C8 = {
        "rdo-baremetal": "http://trunk.rdoproject.org/centos8-%s/component/baremetal/current" % release, # noqa
        "rdo-cinder": "http://trunk.rdoproject.org/centos8-%s/component/cinder/current" % release, # noqa
        "rdo-clients": "http://trunk.rdoproject.org/centos8-%s/component/clients/current" % release, # noqa
        "rdo-cloudops": "http://trunk.rdoproject.org/centos8-%s/component/cloudops/current" % release, # noqa
        "rdo-common": "http://trunk.rdoproject.org/centos8-%s/component/common/current" % release, # noqa
        "rdo-compute": "http://trunk.rdoproject.org/centos8-%s/component/compute/current" % release, # noqa
        "rdo-glance": "http://trunk.rdoproject.org/centos8-%s/component/glance/current" % release, # noqa
        "rdo-manila": "http://trunk.rdoproject.org/centos8-%s/component/manila/current" % release, # noqa
        "rdo-network": "http://trunk.rdoproject.org/centos8-%s/component/network/current" % release, # noqa
        "rdo-octavia": "http://trunk.rdoproject.org/centos8-%s/component/octavia/current" % release, # noqa
        "rdo-security": "http://trunk.rdoproject.org/centos8-%s/component/security/current" % release, # noqa
        "rdo-swift": "http://trunk.rdoproject.org/centos8-%s/component/swift/current" % release, # noqa
        "rdo-tempest": "http://trunk.rdoproject.org/centos8-%s/component/tempest/current" % release, # noqa
        "rdo-tripleo": "http://trunk.rdoproject.org/centos8-%s/component/tripleo/current" % release, # noqa
        "rdo-ui": "http://trunk.rdoproject.org/centos8-%s/component/ui/current" % release, # noqa
        "rdo-component": "http://trunk.rdoproject.org/centos8-%s/component/validation/current" % release, # noqa
        "deps": "http://trunk.rdoproject.org/centos8-%s/deps/latest" % release, # noqa
        "build-deps": "http://trunk.rdoproject.org/centos8-%s/build-deps/latest" % release, # noqa
        "deps-srpm": "http://trunk.rdoproject.org/centos8-%s/deps/latest/SRPMS" % release, # noqa
        "build-srpm": "http://trunk.rdoproject.org/centos8-%s/build-deps/latest/SRPMS" % release, # noqa
        "baseos": "http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/", # noqa
        "appstream": "http://mirror.centos.org/centos/8-stream/AppStream/x86_64/os/", # noqa
        "baseos-srpm": "https://vault.centos.org/centos/8-stream/BaseOS/Source/", # noqa
        "appstream-srpm": "https://vault.centos.org/centos/8-stream/AppStream/Source/", # noqa
    }

    releases = {
        "master": RDO_TRUNK_C8,
        "wallaby": RDO_TRUNK_C8,
        "victoria": RDO_TRUNK_C8,
        "ussuri": RDO_TRUNK_C8,
        "train": RDO_TRUNK_C8,
    }

    return releases[release]


def eprint(*args, **kwargs):
    kwargs.setdefault('file', sys.stderr)
    kwargs.setdefault('flush', True)
    print(*args, **kwargs)


def setup_dnf(release="wallaby"):
    """ Setup dnf query with two repos
    """
    repos = get_repos(release)
    base = dnf.Base()
    # use digest to make repo id unique for each URL
    conf = base.conf
    for name in repos.keys():
        r = base.repos.add_new_repo(
            ("repo-%s" % name),
            conf,
            baseurl=[repos[name]],
            skip_if_unavailable=False,
            gpgcheck=0,
        )
        r.enable()
        r.load()

    base.fill_sack(load_system_repo=False, load_available_repos=True)
    return base.sack.query()


class DepChecker:
    def __init__(self, release, repo=None, source_repo=None, namespace='rpms'):
        self._src_by_bin = None
        self._bin_by_src = None
        self.release = release

        dnfquery = setup_dnf(release=release)
        self.dnfquery = dnfquery
        self.pagure_dict = {}
        self.not_in_repo = []

    def create_mapping(self):
        src_by_bin = {}  # Dict of source pkg objects by binary package objects
        bin_by_src = {}  # Dict of binary pkgobjects by srpm name

        # Populate the dicts
        for rpm_package in self.dnfquery:
            if rpm_package.arch == 'src':
                continue
            srpm = self.SRPM(rpm_package)
            src_by_bin[rpm_package] = srpm
            if srpm:
                if srpm.name in bin_by_src:
                    bin_by_src[srpm.name].append(rpm_package)
                else:
                    bin_by_src[srpm.name] = [rpm_package]

        self._src_by_bin = src_by_bin
        self._bin_by_src = bin_by_src

    @property
    def by_src(self):
        if not self._bin_by_src:
            self.create_mapping()
        return self._bin_by_src

    @property
    def by_bin(self):
        if not self._src_by_bin:
            self.create_mapping()
        return self._src_by_bin

    def find_dependent_packages(self, srpmname, ignore):
        """ Return packages depending on packages built from SRPM ``srpmname``
            that are built from different SRPMS not specified in ``ignore``.

            :param ignore: list of binary package names that will not be
                returned as dependent packages or considered as alternate
                providers
            :type ignore: list() of str()

            :returns: OrderedDict dependent_package: list of requires only
                provided by package ``srpmname`` {dep_pkg: [prov, ...]}
        """
        # Some of this code was stolen from repoquery
        dependent_packages = {}

        # Handle packags not found in the repo
        try:
            rpms = self.by_src[srpmname]
        except KeyError:
            # If we don't have a package in the repo, there is nothing to do
            eprint(f"Package {srpmname} not found in repo")
            self.not_in_repo.append(srpmname)
            rpms = []

        # provides of all packages built from ``srpmname``
        provides = []
        for pkg in rpms:
            # add all the provides from the package as strings
            string_provides = [str(prov) for prov in pkg.provides]
            provides.extend(string_provides)

            # add all files as provides
            # pkg.files is a list of paths
            # sometimes paths start with "//" instead of "/"
            # normalise "//" to "/":
            # os.path.normpath("//") == "//", but
            # os.path.normpath("///") == "/"
            file_provides = [os.path.normpath(f'//{fn}') for fn in pkg.files]
            provides.extend(file_provides)

        # Zip through the provides and find what's needed
        for prov in provides:
            # check only base provide, ignore specific versions
            # "foo = 1.fc20" -> "foo"
            base_provide, *_ = prov.split()

            # FIXME: Workaround for:
            # https://bugzilla.redhat.com/show_bug.cgi?id=1191178
            if base_provide[0] == "/":
                base_provide = base_provide.replace("[", "?")
                base_provide = base_provide.replace("]", "?")

            # Elide provide if also provided by another package
            for pkg in self.dnfquery.filter(provides=base_provide, latest=1):
                # FIXME: might miss broken dependencies in case the other
                # provider depends on a to-be-removed package as well
                if pkg.name in ignore:
                    # eprint(f"Ignoring provider package {pkg.name}")
                    pass
                elif pkg not in rpms:
                    break
            else:
                for dependent_pkg in self.dnfquery.filter(
                        latest=1,
                        requires=base_provide):
                    # skip if the dependent rpm package belongs to the
                    # to-be-removed Fedora package
                    if dependent_pkg in self.by_src[srpmname]:
                        continue

                    # skip if the dependent rpm package is also a
                    # package that should be removed
                    if dependent_pkg.name in ignore:
                        continue

                    # use setdefault to either create an entry for the
                    # dependent package or add the required prov
                    dependent_packages.setdefault(dependent_pkg, set()).add(
                        prov)
        return OrderedDict(sorted(dependent_packages.items()))

    # This function was stolen from pungi
    def SRPM(self, package):
        """Given a package object, get a package object for the
        corresponding source rpm. Requires dnf still configured
        and a valid package object."""
        srpm, *_ = package.sourcerpm.split('.src.rpm')
        sname, sver, srel = srpm.rsplit('-', 2)
        return srpm_nvr_object(self.dnfquery, sname, sver, srel)


def srpm_nvr_object(query, name, version, release):
    try:
        srpmpo = query.filter(name=name,
                              version=version,
                              release=release,
                              latest=1,
                              arch='src').run()[0]
        return srpmpo
    except IndexError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release",
                        choices=["master", "wallaby", "victoria", "ussuri",
                                 "train"],
                        default="master")
    parser.add_argument("--pkg-name")
    args = parser.parse_args()
    eprint('Getting dependants for %s' % args.pkg_name)

    depchecker = DepChecker(args.release)
    dependants = depchecker.find_dependent_packages(args.pkg_name, [])

    for dep in dependants:
        print(dep.name + "-" + dep.evr + "." + dep.arch +
              " from " + str(dep.reponame))
