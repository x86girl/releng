#! /bin/bash
#   Copyright Red Hat, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

function usage() {
    echo "usage: $0 <branch to sync>"
}

function move_changelog() {
  sed -e '1,/%changelog/d' $PKG.spec > Changelog.tmp
  if [[ -e Changelog.old ]]; then
    cat Changelog.old >> Changelog.tmp
  fi
  mv Changelog.{tmp,old}
  git add Changelog.old
}

if [[ $# < 1 ]]; then
    usage
    exit 0
fi

PKG=`basename $PWD`
BRANCH=$1


git pull
git clone git@github.com:openstack-packages/$PKG
pushd $PKG
  git checkout $BRANCH
popd

move_changelog
cp $PKG/$PKG.spec .
git diff
rm *.gz
spectool -g *.spec
fedpkg new-sources  *.gz
fedpkg commit -c
SRPM=$(fedpkg srpm | awk '/Wrote:/ { print $2 }')
koji build --scratch rawhide $SRPM
