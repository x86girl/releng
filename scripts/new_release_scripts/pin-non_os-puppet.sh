#!/bin/bash
set -e

REALPATH=$(realpath "$0")
DIRNAME=$(dirname "$REALPATH")
BASENAME=$(basename "$0")
TMPDIR=/tmp/${BASENAME%.*}
RDOINFO_DIR=$TMPDIR/rdoinfo
VERSIONS_FILE=$TMPDIR/versions.csv
VIRTUAL_ENV=$TMPDIR/.venv
source $DIRNAME/common.rc

MODE=${1:-pin}

mkdir -p $TMPDIR
pushd $TMPDIR >/dev/null 2>&1
echo -e "Working on $TMPDIR directory"
if [[ -d "$RDOINFO_DIR" ]]; then
    echo "rdoinfo repository is already available"
    pushd $RDOINFO_DIR >/dev/null 2>&1
    git fetch origin && git rebase origin/master
    if [[ $? -ne 0 ]]; then
        echo "An error occured when rebasing rdoinfo repository in $RDOINFO_DIR"
        popd >/dev/null
        exit 1
    fi
    popd >/dev/null
else
    git clone $RDOINFO_GIT_URL $TMPDIR/rdoinfo
    if [[ $? -eq 0 ]]; then
        echo "rdoinfo repo is cloned"
    else
        echo "An error occured when cloning rdoinfo repository."
        exit 1
    fi
fi

rm -f $VERSIONS_FILE
curl -sL http://trunk.rdoproject.org/centos9-master/current-tripleo/versions.csv -o $VERSIONS_FILE

echo -e "Creating virtualenv..."
virtualenv -p /usr/bin/python3 $VIRTUAL_ENV >/dev/null
source $VIRTUAL_ENV/bin/activate >/dev/null
echo -e "Installing required modules in virtualenv..."
python -m pip install --upgrade pip >/dev/null
pip install distroinfo >/dev/null
pip install git+https://github.com/rdo-infra/releng >/dev/null
echo -e "Creating of virtualenv OK"

grep ^puppet $VERSIONS_FILE |awk -F, '{print $1 " "$2 "  " $3}'|while read pkg repo commit
do
    if [ $(echo $repo|grep -c opendev) -eq 0 ]; then
        python $DIRNAME/update-tag.py $RDOINFO_DIR $MASTER_RELEASE-uc $pkg $commit $MODE
    fi
done
deactivate

pushd $RDOINFO_DIR >/dev/null 2>&1
git add tags/${MASTER_RELEASE}-uc.yml
git commit -m "Pin non-openstack puppet modules for ${MASTER_RELEASE^}"
popd >/dev/null

echo -e "\nYou can check results in $RDOINFO_DIR"
echo -e "If everyting's fine you can run the command: git review -t ${MASTER_RELEASE}-branching"

