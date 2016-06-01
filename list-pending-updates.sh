#! /bin/bash


declare -a on_exit_items

function on_exit() {
    # remove tempfiles registered
    for i in "${on_exit_items[@]}"; do
        rm $i
    done
}
# setup trap on EXIt to cleanup temp files
trap on_exit EXIT


function createtmpfile() {
    tmpfile=`mktemp`
    local n=${#on_exit_items[*]}
    on_exit_items[$n]=$tmpfile
    echo $tmpfile
}


function diff_tags() {
    release=`createtmpfile`
    testing=`createtmpfile`
    if [[ $1 == "common" ]]; then
        echo "======= Pending updates from $1-pending ======="
        cbs list-tagged --quiet --latest cloud7-openstack-$1-pending | sort | awk '{ print $1 }'
    fi
    echo "======= Pending updates from $1-testing ======="
    
    cbs list-tagged --latest cloud7-openstack-$1-release | sort | awk '{ print $1 }' > release
    cbs list-tagged --latest cloud7-openstack-$1-testing | sort | awk '{ print $1 }' > testing

    diff --unified=0 --minimal release testing
}


function usage() {
    echo "Usage: $0 <list of release [common, mitaka, newton, ..]>"
    exit 0
}


if [[ $# < 1 ]]; then
    usage
fi


for rel in "$@"; do
    diff_tags $rel
done
