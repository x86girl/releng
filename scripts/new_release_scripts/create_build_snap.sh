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
echo "Last release in ${LATEST_RELEASE}: $LAST_NVR"

NEWCOMMIT=$(echo "$PACKAGE_INFO" |grep -A1 ${MASTER_RELEASE_TAG}|grep source-branch|awk '{print $2}')
echo "New commit is $NEWCOMMIT"

rm -rf $PKG
rdopkg clone $PKG >/dev/null 2>&1
pushd $PKG
git checkout -b $MASTER_RELEASE-rdo --track origin/$MASTER_RELEASE-rdo>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: branch $MASTER_RELEASE-rdo does not exist"
    exit 1
fi

git checkout rpm-master >/dev/null 2>&1
git checkout -b $LATEST_RELEASE-rdo --track origin/$LATEST_RELEASE-rdo >/dev/null 2>&1
CURRENTCOMMIT=$(grep "^%global commit" *spec|awk '{print $3}')

if [ -z $CURRENTCOMMIT  ];then
    echo "ERROR: missing snapsot macros in the spec"
    exit 1
fi

CURRENTVERSION=$(grep ^Version *spec|awk '{print $2}')
CURRENTRELEASE=$(grep ^Release *spec|awk '{print $2}'|awk -F '%' '{print $1}')

echo -e "Current version\t $CURRENTVERSION"
echo -e "Current release\t $CURRENTRELEASE"

if [ $NEWCOMMIT == $CURRENTCOMMIT ]; then
    echo "No new commit detected, cross-tag required"
    echo "cbs add-pkg cloud9s-openstack-$MASTER_RELEASE-candidate $PKG --owner=rdobuilder"
    echo "cbs tag-build cloud9s-openstack-$MASTER_RELEASE-candidate $LAST_NVR"
    echo "Press 2 key to run the 2 commands above:"
    read -n 2
    cbs add-pkg cloud9s-openstack-$MASTER_RELEASE-candidate $PKG --owner=rdobuilder
    cbs tag-build cloud9s-openstack-$MASTER_RELEASE-candidate $LAST_NVR
    exit 0
fi

git checkout $NEWCOMMIT >/dev/null 2>&1

if [ -f metadata.json ]; then
    NEWVERSION=$(grep -w '"version":' metadata.json |awk '{print $2}'| tr -d '\",')
else
    NEWVERSION=$(grep -w ^version Modulefile |awk '{print $2}'| tr -d \'\")
fi

if [[ -z $NEWVERSION ]]; then
    echo "ERROR: missing new version"
    exit 1
fi

if [[ "$NEWVERSION" == *"-rc"* ]]; then
    NEWVERSION=$(echo $NEWVERSION | cut -d- -f1)
    IS_RC=true
else
    IS_RC=false
fi


echo -e "New version\t $NEWVERSION"

if [ $CURRENTVERSION != $NEWVERSION ]; then
    if $IS_RC; then
        NEWRELEASE=0.1
    else
        NEWRELEASE=1
    fi
else
    if [ `echo $CURRENTRELEASE | grep -c -e "."` -eq 0 ]; then
        NEWRELEASE=$((CURRENTRELEASE+1))
    else
        BASE=$(echo $CURRENTRELEASE | cut -d. -f2)
        NEWRELEASE="0.$((BASE+1))"
    fi
fi

echo -e "New release\t $NEWRELEASE"

git checkout $MASTER_RELEASE-rdo >/dev/null 2>&1

sed -i "s/^Version.*/Version:        ${NEWVERSION}/" *.spec
sed -i "s/^%global commit.*/%global commit ${NEWCOMMIT}/" *.spec
if $IS_RC; then
    MILESTONE=".0rc0"
    grep -e "%global milestone $MILESTONE" *.spec 2>&1 >/dev/null || sed -i "1 s/^/%global milestone $MILESTONE\n/" *.spec
    sed -i "s/^Release.*/Release:        ${NEWRELEASE}%{?milestone}%{?alphatag}%{?dist}/" *.spec
    source_base_url=$(grep -e "^Source0" *.spec | cut -d/ -f 1-5)
    new_url="$source_base_url/archive/%{commit}.tar.gz#/%{upstream_name}-%{shortcommit}.tar.gz"
    sed -i "s|^Source0:.*|$new_url|g" *.spec
else
    MILESTONE=""
    sed -i "s/^Release.*/Release:        ${NEWRELEASE}%{?alphatag}%{?dist}/" *.spec
fi

is_changes=$(git diff)
if [[ -n "$is_changes" ]]; then
    CHANGELOG="* $(date +"%a %b %d %Y") RDO <dev@lists.rdoproject.org> ${NEWVERSION}-${NEWRELEASE}${MILESTONE}.$(echo $NEWCOMMIT|cut -c -7)git\n- Update to post $NEWVERSION \($NEWCOMMIT\)\n"
    sed -i "/^%changelog/a $CHANGELOG" *spec
else
    echo "The SPEC file is already up-to-date"
    exit 0
fi

echo "Last build in RDO Trunk is:"
repoquery --repofrompath=rdo,http://trunk.rdoproject.org/centos9-${MASTER_RELEASE}/component/tripleo/current/ --disablerepo=* --enablerepo=rdo $PKG 2>/dev/null

echo -e "Checking if sources are available"
SOURCE_URLS=$(spectool -g *.spec --dry-run | cut -d: -f2- 2>/dev/null)
for url in $SOURCE_URLS; do
    curl --silent -L --fail --request GET -o /dev/null --head $url
    if [ $? -ne 0 ]; then
        echo "ERROR: $url is not available"
        exit 1
    fi
done

git commit -a -m "Update to post $NEWVERSION ($NEWCOMMIT)"
git show
git branch

echo "Press 2 key to submit review to Gerrit:"
read -n 2

git review -t ${MASTER_RELEASE}-branching
git show

popd
