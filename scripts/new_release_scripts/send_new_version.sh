PKG=$1

version=train

rm -rf $PKG

rdopkg clone $PKG >/dev/null 2>&1
pushd $PKG
git remote update
git checkout $version-rdo
if [ $? != 0 ]
then
    git checkout --track origin/$version-rdo
    if [ $? -ne 0 ]; then
        echo "ERROR checking out $version-rdo in $PKG"
        continue
    fi 
fi
git pull
TAG=`git describe --abbrev=0 upstream/stable/$version 2>/dev/null`
if [ $? -ne 0 ]; then
echo "NOT stable $version tag found, checking MASTER"
TAG=`git describe --tag --abbrev=0 upstream/master 2>/dev/null`
fi
echo "New version detected $TAG"
rdopkg info $PKG |grep -A1 $version-uc
#

read -n 2

rdopkg new-version -U -b $TAG -u RDO -e dev@lists.rdoproject.org -t
if [ $? -eq 0 ]
then
    git review -t $version-branching
else
    echo "ERROR runing rdopkg new-version for $PKG"
fi
popd
