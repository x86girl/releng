PKG=$1
RELEASE=ussuri
RELEASE_TAG=ussuri-uc
PREV_RELEASE=train

LASTRELEASE=$(rdopkg findpkg $PKG| grep cloud8-openstack-${PREV_RELEASE}-testing|awk '{print $2}')
echo "Last release in ${PREV_RELEASE}: $LASTRELEASE"

NEWCOMMIT=$(rdopkg findpkg $PKG|grep -A1 ${RELEASE_TAG}|grep source-branch|awk '{print $2}')

echo "New commit is $NEWCOMMIT"

rm -rf $PKG
rdopkg clone $PKG >/dev/null 2>&1
pushd $PKG
git branch -D $RELEASE-rdo>/dev/null 2>&1
git checkout -b $RELEASE-rdo --track origin/$RELEASE-rdo>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: branch $RELEASE-rdo does not exist"
    exit 1
fi

git checkout rpm-master >/dev/null 2>&1
git branch -D $PREV_RELEASE-rdo >/dev/null 2>&1
git checkout -b $PREV_RELEASE-rdo --track origin/$PREV_RELEASE-rdo >/dev/null 2>&1
CURRENTCOMMIT=$(grep "^%global commit" *spec|awk '{print $3}')

if [ -z $CURRENTCOMMIT  ];then
    echo "ERROR: missing snapsot macros in the spec"
    exit 1
fi

CURRENTVERSION=$(grep ^Version *spec|awk '{print $2}')
CURRENTRELEASE=$(grep ^Release *spec|awk '{print $2}'|awk -F '%' '{print $1}')

echo "Current version $CURRENTVERSION"
echo "Current release $CURRENTRELEASE"

if [ $NEWCOMMIT == $CURRENTCOMMIT ]; then
    echo "No new commit detected, cross-tag required"
    echo "cbs tag-build cloud8-openstack-$RELEASE-candidate $LASTRELEASE"
    read -n 2
    cbs add-pkg cloud8-openstack-$RELEASE-candidate $PKG --owner=rdobuilder
    cbs tag-build cloud8-openstack-$RELEASE-candidate $LASTRELEASE
    exit 0
fi

git checkout $NEWCOMMIT >/dev/null 2>&1

if [ -f metadata.json ]; then
    NEWVERSION=$(grep -w '"version":' metadata.json |awk '{print $2}'| tr -d '\",')
else
    NEWVERSION=$(grep -w ^version Modulefile |awk '{print $2}'| tr -d \'\")
fi


echo "New version $NEWVERSION"

if [ $CURRENTVERSION != $NEWVERSION ]; then
    NEWRELEASE=1
else
    NEWRELEASE=$((CURRENTRELEASE+1))
fi

echo "New release $NEWRELEASE"

git checkout $RELEASE-rdo >/dev/null 2>&1

sed -i "s/^Version.*/Version:        ${NEWVERSION}/" *.spec
sed -i "s/^Release.*/Release:        ${NEWRELEASE}%{?alphatag}%{?dist}/" *.spec
sed -i "s/^%global commit.*/%global commit ${NEWCOMMIT}/" *.spec

CHANGELOG="* $(date +"%a %b %d %Y") RDO <dev@lists.rdoproject.org> ${NEWVERSION}-${NEWRELEASE}.$(echo $NEWCOMMIT|cut -c -7)git\n- Update to post $NEWVERSION \($NEWCOMMIT\)\n"

sed -i "/^%changelog/a $CHANGELOG" *spec

echo "Last build in RDO Trunk is:"



repoquery --repofrompath=rdo,http://trunk.rdoproject.org/centos7-${RELEASE}/current --disablerepo=* --enablerepo=rdo $PKG 2>/dev/null|grep $PKG

git commit -a -m "Update to post $NEWVERSION ($NEWCOMMIT)"

git show

git branch

read -n 2

git review -t ${RELEASE}-branching
git show

popd
