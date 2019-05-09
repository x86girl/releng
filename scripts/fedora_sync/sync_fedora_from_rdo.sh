#!/bin/bash

# This script update the spec in fedora from the latest build in CBS in RDO, pushes it to fedora
# and rebuilds.

PKG=$1
BASEDIR=$2

# Adjust as needed
FEDUSER=amoralej
FEDORA_RELEASE=34
RDO_RELEASE=victoria
CHANGELOG_NAME="Alfredo Moralejo"
CHANGELOG_MAIL=amoralej@redhat.com
#

FEDORA_TAG=f${FEDORA_RELEASE}
FEDORA_DIST=fc${FEDORA_RELEASE}

INITIAL_DIR=$PWD

mkdir -p $BASEDIR

if [ -z $3 ]; then
NVR=$(cbs latest-build --quiet cloud8-openstack-${RDO_RELEASE}-release $PKG|grep $PKG|awk '{print $1}')
else
NVR=$3
fi

NVR_FED=$(koji latest-build --quiet ${FEDORA_TAG} $PKG|grep $PKG|awk '{print $1}')

echo $NVR $NVR_FED

rpmdev-vercmp $NVR $NVR_FED >/dev/null 2>&1
if [ $? -ne 11 ];then
  echo "INFO: build $NVF_FED in Fedora is higher that CBS $NVR"
  exit 0
fi

function preprocess(){
  SPEC=$1
  # openstack-macros does not exist in fedora.
  sed -i '/Requires: *openstack-macros/d;s/%py_req_cleanup/rm -rf *requirements.txt/g' $SPEC
}

function prepare_spec(){
  PKGNAME=$1
  PKGNVR=$2
  mkdir -p $BASEDIR/$PKGNAME
  pushd $BASEDIR/$PKGNAME
  rm *rpm
  cbs download-build -a 'src' $PKGNVR
  mkdir -p $BASEDIR/$PKGNAME/rpmbuild/SPECS \
           $BASEDIR/$PKGNAME/rpmbuild/BUILD \
           $BASEDIR/$PKGNAME/rpmbuild/SOURCES \
           $BASEDIR/$PKGNAME/rpmbuild/BUILDROOT \
           $BASEDIR/$PKGNAME/rpmbuild/SRPMS \
           $BASEDIR/$PKGNAME/rpmbuild/RPMS

  echo "%_topdir $BASEDIR/$PKGNAME/rpmbuild" > ~/.rpmmacros
  rpm -ivh *src.rpm

  pushd $BASEDIR/$PKGNAME/rpmbuild/SPECS
  preprocess $PWD/*spec
  popd
  popd
}

function rebuild_srpm(){
  PKGNAME=$1
  echo "%_topdir $BASEDIR/$PKGNAME/rpmbuild" > ~/.rpmmacros
  pushd $BASEDIR/$PKGNAME/rpmbuild/SPECS
  rpmbuild --define "dist .${FEDORA_DIST}" -bs *spec
  popd
  rm ~/.rpmmacros
}

function scratch_build(){
  PKGNAME=$1
  PKGNVR=$2
  koji build --wait --scratch $FEDORA_TAG $BASEDIR/$PKGNAME/rpmbuild/SRPMS/*src.rpm|tee $BASEDIR/$NVR.out
  TASKID=$(grep buildArch $BASEDIR/${NVR}.out|head -1|awk '{print $1}')
  tail -1 $BASEDIR/${NVR}.out >> $BASEDIR/results.out
  koji taskinfo $TASKID|grep rpm$ >> $BASEDIR/generated_packages.txt
}

function rebuild_package(){
  PKGNAME=$1
  PKGNVR=$2
  echo "INFO: rebuilding $PKGNVR"
  rm -rf $BASEDIR/$PKGNAME/fedora
  mkdir -p $BASEDIR/$PKGNAME/fedora
  pushd $BASEDIR/$PKGNAME/fedora
  fedpkg clone $PKGNAME
  pushd $PKGNAME
  sed '0,/^\%changelog/d' *spec > changelog.txt
  cp $BASEDIR/$PKGNAME/rpmbuild/SPECS/*.spec .
  sed -i '$,/^$/d' *spec
  sed -i '/^\%changelog/,$d' *spec
  echo "%changelog" >> *spec
  cat changelog.txt >> *spec
  python $INITIAL_DIR/update_changelog.py *spec "$CHANGELOG_NAME" "$CHANGELOG_MAIL"
  spectool -g *spec
  rm changelog.txt
  fedpkg new-sources *tar.gz *txt *asc
  git commit -a -m "Sync from RDO ${RDO_RELEASE} release from $PKGNVR"
  fedpkg push
  fedpkg build
  popd
  popd
}

if [ ! -z $NVR ]; then
  pushd $BASEDIR
  prepare_spec $PKG $NVR
  rebuild_srpm $PKG $NVR
  scratch_build $PKG $NVR
  tail -1 $BASEDIR/${NVR}.out|grep -q completed
  if [ $? -eq 0 ];then
     rebuild_package $PKG $NVR
  fi
  popd
fi

