#!/usr/bin/env bash
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
#
# before you run this modify your ~/.ssh/config to create a
# review.rdoproject.org entry:
#
#Host review.rdoproject.org
#   User <yourgerritusername>
#   Port 29418
#
# By default this script will:
# Abandon reviews in rpm-master branch in all projects which are older than 12 weeks
#
# Some Examples:-
# bash abandon_old_reviews.sh --dry-run --branch master --project config --older 70
# bash abandon_old_reviews.sh --dry-run --project openstack/nova-distgit --older 30
# bash abandon_old_reviews.sh --dry-run --branch ^.*-rdo --project ^openstack/.*-distgit
#
# Run without --dry-run to abandon patches

DRY_RUN=0
BRANCH=rpm-master
CLEAN_PROJECT=""
WEEKS=12

function print_help {
    echo "Script to abandon patches without activity for more than ${WEEKS} weeks."
    echo "Usage:"
    echo "      ./abandon_old_reviews.sh [--dry-run] [--project <project_name>]"
    echo "                               [--branch <branch_name>] [--older <no_of_weeks>] [--help]"
    echo " --dry-run                    In dry-run mode it will only print what patches would be abandoned "
    echo "                              but will not take any real actions in gerrit"
    echo " --project <project_name>     Only check patches from <project_name> if passed."
    echo "                              It must be one of the projects which are a part of the Neutron stadium."
    echo "                              If project is not provided, all projects from the Neutron stadium will be checked"
    echo " --branch <branch_name>       Only check patches from from specific branch if <branch_name> is passed."
    echo "                              By Default branch rpm-master will be checked"
    echo " --older <no_of_weeks>        Number of weeks for which reviews needs to be cleaned"
    echo "                              By Default script will look for patches older than 12 weeks"
    echo " --help                       Print help message"
}

while [ $# -gt 0 ]; do
    key="${1}"

    case $key in
        --dry-run)
            echo "Enabling dry run mode"
            DRY_RUN=1
            shift # past argument
        ;;
        --project)
            CLEAN_PROJECT="project:${2}"
            shift # past argument
            shift # past value
        ;;
        --branch)
            BRANCH="${2}"
            shift # past argument
            shift # past value
        ;;
        --older)
            WEEKS="${2}"
            shift # past argument
            shift # past value
        ;;
        --help)
            print_help
            exit 2
    esac
done

set -o errexit
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function abandon_review {
    local gitid=$1
    shift
    local msg=$@
    if [ $DRY_RUN -eq 1 ]; then
        echo "Would abandon $gitid"
    else
        echo "Abandoning $gitid"
        ssh review.rdoproject.org gerrit review $gitid --abandon --message \"$msg\"
    fi
}

target_reviews=$(ssh review.rdoproject.org "gerrit query branch:${BRANCH} ${CLEAN_PROJECT} --current-patch-set --format json status:"open" age:${WEEKS}w NOT is:mergeable" | jq .currentPatchSet.revision | grep -v null | sed 's/"//g')

abandon_msg=$(cat <<EOF
This review is > ${WEEKS} weeks and is in Merge conflict, so possibly it's
a FTBFS review which is fixed with some other review, we are abandoning
this for now. Feel free to reactivate the review by pressing the
restore button if it's a valid patch and is still required.
EOF
)

for review in $target_reviews; do
    echo "Abandon review https://review.rdoproject.org/r/#/q/$review"
    abandon_review $review $abandon_msg
done
