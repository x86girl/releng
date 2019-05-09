#!/bin/bash
# This script lists all OpenStack packages listed in rdoinfo with tag:<RDOINFO_TAG> which
# exist in the fedora tag specified in f31. This list can be used to update packages using
# script sync_fedora_from_rdo.sh

# Requires to have rdopkg and koji packages installed.

RDOINFO_TAG=$1
KOJI_TAG=$2

rdopkg info "tags:$RDOINFO_TAG"|grep ^name|awk '{print $2}'|while read pkg
do
    koji latest-build $KOJI_TAG $pkg|grep -q $pkg
    if [ $? -eq 0 ];then
        echo $pkg
    fi
done

