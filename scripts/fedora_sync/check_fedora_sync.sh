#!/bin/bash

# This script check the version of a package in a version of Fedora and compares it with latest
# version in CBS for a rdo release.

PKG=$1

FEDORA_RELEASE=$2
RDO_RELEASE=$3

FEDORA_TAG=f${FEDORA_RELEASE}
CBS_TAG_PREFIX="cloud8"

CBS_TAGS=$(cbs list-tags|grep ${RDO_RELEASE}-release)
# By default, it will pick up the stream tag prefix.
CBS_TAG=$(echo "$CBS_TAGS"|grep -e "^${CBS_TAG_PREFIX}s" || echo "$CBS_TAGS"|grep -e ^"${CBS_TAG_PREFIX}")

NVR=$(cbs latest-build --quiet ${CBS_TAG} $PKG|grep $PKG|awk '{print $1}')

NVR_FED=$(koji latest-build --quiet ${FEDORA_TAG} $PKG|grep $PKG|awk '{print $1}')

rpmdev-vercmp $NVR $NVR_FED >/dev/null 2>&1
if [ $? -ne 11 ];then
  echo "INFO: build $NVR_FED in Fedora is higher that CBS $NVR"
else
  echo "ERROR: build $NVR_FED in Fedora is lower that CBS $NVR"
fi


