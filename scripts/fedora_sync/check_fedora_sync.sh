#!/bin/bash

# This script check the version of a package in a version of Fedora and 
# compares it with latest  version in CBS for a rdo release.

if [[ $# -ne 4 ]]; then
        echo "Usage: $0 <PKG> <FEDORA_RELEASE> <RDO_RELEASE>"
        echo "E.g.: $0 python-sushy 42 caracal"
        exit 1
fi

PKG=$1

FEDORA_RELEASE=$2
FEDORA_TAG=f${FEDORA_RELEASE}

RDO_RELEASE=$3

CBS_TAG_PREFIX="cloud9s"
CBS_TAG=${CBS_TAG_PREFIX}-openstack-${RDO_RELEASE}-release

NVR=$(cbs latest-build --quiet ${CBS_TAG} $PKG|grep $PKG | awk '{print $1}')
NVR_FED=$(koji latest-build --quiet ${FEDORA_TAG} $PKG | grep $PKG | awk '{print $1}')

rpmdev-vercmp $NVR $NVR_FED >/dev/null 2>&1
if [ $? -ne 11 ];then
  echo "INFO: build $NVR_FED in Fedora is higher that CBS $NVR"
else
  echo "ERROR: build $NVR_FED in Fedora is lower that CBS $NVR"
fi
