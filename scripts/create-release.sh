#!/bin/bash
#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
#   original author: Frédéric Lepied <flepied@redhat.com>

if [ $# -lt 2 ]; then
    echo "$0 <branch> <milestone> <changelog message>" 1>&2
    echo "Example: $0 mitaka Rebuild for Mitaka" 1>&2
    exit 1
fi

set -ex

branch="$1-rdo"
basetag="cloud7-openstack-$1"
buildtarget="cloud7-openstack-$1-el7"
owner="hguemar" # FIXME: should be a valid CBS account
shift 1
changelog="$*"

pkg=$(basename $PWD _distro)
spec=$(ls *.spec)

cd ../$pkg
git fetch --all -t
git reset --hard
git pull
git checkout .
tag=$(git describe --abbrev=0 --tags)
# extract the milestone name
mname=${tag##*.0}
milestone=.0${mname}

# try to filter out bad milestone names
case "$mname" in
    rc*)
        ;;
    b*)
        ;;
    *)
        milestone=
        ;;
esac

if [ -z "$mname" ]; then
    milestone=
fi

git checkout ${tag}
# call python setup.py twice as pbr could output something on the first run
python setup.py --version
pyver=$(python setup.py --version)

if [ -n "$milestone" ]; then
    version=$(echo ${pyver}|sed "s/${milestone}.*$//")
else
    version=$(echo ${pyver}|sed "s/.dev.*$//")
fi

# no milestone
if [ "${pyver}" = "${version}" ]; then
    milestone=
fi

git checkout master

cd ../${pkg}_distro
git pull
git checkout .

# already done
if git branch -a|grep -q "/${branch}\$"; then
    echo "branch already created"
else
    git checkout -b ${branch} rpm-master
fi

if [ -n "$milestone" ]; then
    sed -i -e "1i%global milestone $milestone" ${spec}
fi

if [ -n "$milestone" ]; then
    sed -i -e "s/\(Version:\s*\)XXX/\1$version/" -e 's/\(Release:\s*\)XXX/\10.1%{?milestone}%{?dist}/' ${spec}
    release="0.1"
else
    sed -i -e "s/\(Version:\s*\)XXX/\1$version/" -e 's/\(Release:\s*\)XXX/\11%{?dist}/' ${spec}
    release="1"
fi

if ! egrep -q 'Source0:.*%{?(milestone|upstream_version)}?\.tar.*' ${spec}; then
    sed -i -e 's/\(Source0:.*\)\(\.tar.*\)/\1%{?milestone}\2/' ${spec}
fi
sed -i -e 's/\(Source0:.*\)-master\(.*\)/\1-%{version}\2/' ${spec}

if ! grep -qF '%{!?upstream_version: ' ${spec}; then
    sed -i -e 's/Name:.*/\n%{!?upstream_version: %global upstream_version %{version}%{?milestone}}\n\n&/' ${spec}
fi

RPM_DATE=$(LC_TIME=C date -u +"%a %b %e %Y")
echo "* ${RPM_DATE} RDO <rdo-list@redhat.com> ${version}-${release}${milestone}" >> ${spec}
echo "- ${changelog} ${mname}" >> ${spec}

git diff
spectool -g ${spec}
rm .gitreview
git commit -m "${changelog} ${mname}" -a
srpm=$(fedpkg --dist el7 srpm | awk 'function basename(file) { sub(".*/", "", file); return file } /Wrote:/ { print basename($2) }')
for i in candidate testing release; do cbs add-pkg $basetag-$i `basename $PWD _distro` --owner $owner; done
cbs build --scratch $buildtarget $srpm
exit 1
git checkout rpm-master
git review -s
git push --set-upstream gerrit $branch

# create-release.sh ends here
