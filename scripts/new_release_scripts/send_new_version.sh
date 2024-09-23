#!/bin/bash

REALPATH=$(realpath "$0")
DIRNAME=$(dirname "$REALPATH")
source $DIRNAME/common.rc
LANG=en_US.UTF-8

function get_current_nvr_in_trunk() {
    local pkg=$1
    local component=$2
    CURRENT_NVR_IN_TRUNK=$(repoquery --repofrompath=rdo,http://trunk.rdoproject.org/centos9-${MASTER_RELEASE}/component/$component/current/ --disablerepo=* --enablerepo=rdo --nvr $pkg 2>/dev/null)
}


PKG=$1

echo -e "Fetching $PKG medatadata from rdoinfo..."
PACKAGE_INFO=$(rdopkg findpkg $PKG)

echo -e "Cloning $PKG repo..."
rm -rf $PKG
rdopkg clone $PKG >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR when cloning $PKG"
    exit 1
fi

pushd $PKG >/dev/null
git checkout -b $MASTER_RELEASE-rdo --track origin/$MASTER_RELEASE-rdo>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: branch $MASTER_RELEASE-rdo does not exist in distgit repo"
    exit 1
else
    echo "The branch ${MASTER_RELEASE}-rdo exists in distgit repo"
fi

LAST_NVR=$(echo "$PACKAGE_INFO" | grep cloud9s-openstack-${LATEST_RELEASE}-release|awk '{print $2}')
LAST_VERSION=$(echo -e "$LAST_NVR" | rev | cut -d- -f2 | rev)
echo -e "The latest NVR in ${LATEST_RELEASE} is:\t $LAST_NVR"

CURRENT_TAG=$(echo "$PACKAGE_INFO" |grep -e "${MASTER_RELEASE}-uc"|awk '{print $2}')
echo -e "The current tag is:\t\t $CURRENT_TAG"

COMPONENT=$(echo "$PACKAGE_INFO" | grep -e "component"|awk '{print $2}')
get_current_nvr_in_trunk $PKG $COMPONENT
echo -e "Last build in RDO Trunk is:\t $CURRENT_NVR_IN_TRUNK"

TAG=`git describe --abbrev=0 upstream/stable/$MASTER_RELEASE 2>/dev/null`
if [ $? -ne 0 ]; then
    echo "There is NOT stable tag found for '$MASTER_RELEASE', checking on 'master' tag."
    TAG=`git describe --tag --abbrev=0 upstream/master 2>/dev/null`
fi
echo -e "Latest version detected:\t $TAG"

if [ $TAG == $LAST_VERSION ]; then
    echo "No new version detected, a cross-tag is required. Cherry-picking from last release..."
    git checkout ${MASTER_RELEASE}-rdo
    git cherry-pick -x origin/${LATEST_RELEASE}-rdo
    git show
else
    rdopkg new-version -U -b $TAG -u RDO -e dev@lists.rdoproject.org -t -d
    bash $DIRNAME/edit_source_gpg_sign && git commit -a --amend --no-edit
fi

echo "Press 2 key to submit review to Gerrit:"
read -n 2

git review -t ${MASTER_RELEASE}-branching

popd >/dev/null
