#!/bin/bash

# This script aims to pin recentely branched tempest plugin projects to latest tag.
# releng repo is required to be installed before exexuting script.

set -e

DIRNAME=$(basename $0 | cut -d. -f1)
WORKDIR="/tmp/$DIRNAME"

RDOINFO_GIT_URL="https://github.com/redhat-openstack/rdoinfo.git"
RELENG_GIT_URL="https://github.com/rdo-infra/releng.git"
MASTER_RELEASE="$(rdopkg info | grep -e "in development phase" | awk '{print $1}')"
TEMPEST_PROJECTS=$(rdopkg info -t $MASTER_RELEASE-uc conf:tempest tags:$MASTER_RELEASE-uc \
                 | grep "name: " | sort | sed 's/name: //g'| sed "s/python-\(.*\)-tests-tempest/\1-tempest-plugin/")

TEMPEST_PROJECTS="${TEMPEST_PROJECTS}
tempest"

if [ ! -d $WORKDIR ]; then
mkdir $WORKDIR
fi

pushd $WORKDIR/ >/dev/null
if [ ! -d $WORKDIR/rdoinfo ]; then
    git clone $RDOINFO_GIT_URL
fi

if [ ! -d $WORKDIR/releng ]; then
    git clone $RELENG_GIT_URL
fi

pushd $WORKDIR/releng/rdoutils >/dev/null

while IFS= read -r project; do
        if [[ "$project" =~ "openstack-sahara-tests" ]]; then
            project="sahara-tests"
        fi
        upstream=$(rdopkg findpkg $project | grep upstream | awk '{print $2}')
        latest_tag=$(git ls-remote --tags --refs $upstream 2>/dev/null | cut -d '/' -f3 | grep -e "[0-9]\." | sort --version-sort | tail -n 1)
        python3 -c "from rdoinfo import update_tag; update_tag('tags', '$project', '${MASTER_RELEASE}-uc', {'source-branch': '$latest_tag'}, local_dir='$WORKDIR/rdoinfo', update_all_files=False)"
        echo "Updating project $project for ${MASTER_RELEASE}-uc with latest tag $latest_tag."
        echo
done <<< "$TEMPEST_PROJECTS"

popd >/dev/null
popd >/dev/null
