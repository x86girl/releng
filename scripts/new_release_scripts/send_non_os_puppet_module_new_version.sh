#!/bin/bash
set -e

REALPATH=$(realpath "$0")
DIRNAME=$(dirname "$REALPATH")
source $DIRNAME/common.rc
LANG=en_US.UTF-8
MASTER_RELEASE_TAG=${MASTER_RELEASE}-uc

PKG=$1

PACKAGE_INFO=$(rdopkg findpkg $PKG)

LAST_NVR=$(echo "$PACKAGE_INFO" | grep cloud9s-openstack-${LATEST_RELEASE}-release|awk '{print $2}')
echo "Latest NVR in ${LATEST_RELEASE}: $LAST_NVR"

TAG_IN_LATEST_RELEASE=$(echo "$PACKAGE_INFO" |grep -A2 ${LATEST_RELEASE}|grep source-branch|awk '{print $2}')
echo "Tag in ${LATEST_RELEASE}: $TAG_IN_LATEST_RELEASE"

TAG_IN_MASTER_RELEASE=$(echo "$PACKAGE_INFO" |grep -A2 ${MASTER_RELEASE_TAG}|grep source-branch|awk '{print $2}')
echo "Tag in ${MASTER_RELEASE_TAG}: $TAG_IN_MASTER_RELEASE"

rm -rf $PKG
rdopkg clone $PKG >/dev/null 2>&1
pushd $PKG >/dev/null 2>&1
git checkout -b $MASTER_RELEASE-rdo --track origin/$MASTER_RELEASE-rdo>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: branch $MASTER_RELEASE-rdo does not exist"
    exit 1
fi

TAG_IN_MASTER_RELEASE=1
TAG_IN_LATEST_RELEASE=1
if [ $TAG_IN_MASTER_RELEASE == $TAG_IN_LATEST_RELEASE ]; then
    echo -e "The version is the same as previous release.\nYou can proceed with a cherry-pick operation."
    exit 0
fi

NEWVERSION=$(echo "$TAG_IN_MASTER_RELEASE" | sed 's/v//')
NEWRELEASE=1

git checkout $MASTER_RELEASE-rdo >/dev/null 2>&1

sed -i "s/^Version.*/Version:        ${NEWVERSION}/" *.spec
sed -i "s/^Release.*/Release:        ${NEWRELEASE}%{?dist}/" *.spec

is_changes=$(git diff)
if [[ -n "$is_changes" ]]; then
    CHANGELOG="* $(date +"%a %b %d %Y") RDO <dev@lists.rdoproject.org> ${NEWVERSION}-${NEWRELEASE}\n- Update to $NEWVERSION\n"
    sed -i "/^%changelog/a $CHANGELOG" *spec
else
    echo "The SPEC file is already up-to-date"
    exit 0
fi

echo "Latest build in RDO Trunk is:"
repoquery --repofrompath=rdo,http://trunk.rdoproject.org/centos9-${MASTER_RELEASE}/component/puppet/current/ --disablerepo=* --enablerepo=rdo $PKG 2>/dev/null

echo -e "Checking if sources are available"
SOURCE_URLS=$(spectool -g *.spec --dry-run | cut -d: -f2- 2>/dev/null)
for url in $SOURCE_URLS; do
    curl --silent -L --fail --request GET -o /dev/null --head $url
    if [ $? -ne 0 ]; then
        echo "ERROR: $url is not available"
        exit 1
    fi
done

git commit -a -m "Update to $NEWVERSION"
git branch
git show --color=always |less -r

echo "Press 2 key to submit review to Gerrit:"
read -n 2

git review -t ${MASTER_RELEASE}-branching

popd >/dev/null 2>&1
