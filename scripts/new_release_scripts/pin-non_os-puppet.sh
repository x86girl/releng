#!/bin/bash
RELEASE=wallaby
RDOINFO_DIR=/home/$USER/rdoinfo
MODE=${1:-pin}

if [ ! -d $RDOINFO_DIR ];then
    echo "$RDOINFO_DIR doesn't exist, clone latest rdoinfo first"
    exit 1
fi

rm -f versions.csv

wget http://trunk.rdoproject.org/centos8-master/current-tripleo/versions.csv

grep ^puppet versions.csv |awk -F, '{print $1 " "$2 "  " $3}'|while read pkg repo commit
do
    if [ $(echo $repo|grep -c opendev) -eq 0 ]; then
        python $(dirname $0)/update-tag.py $RDOINFO_DIR $RELEASE-uc $pkg $commit $MODE
    fi
done

