#!/bin/bash
set -e


WORKDIR=/tmp/"$(basename -s .sh $0)"
LOGS="$WORKDIR"/branching_log

RSRC_REPO_NAME="config"
RSRC_REPO_URL="https://review.rdoproject.org/r/$RSRC_REPO_NAME"
RSRC_DIR="$WORKDIR/$RSRC_REPO_NAME"

RELEASES=$(rdopkg info)
MASTER_RELEASE=$(echo -e "$RELEASES" | grep -e "in development phase" | awk '{print $1}')
LATEST_RELEASE=$(echo -e "$RELEASES" | grep -e "in maintained phase" | awk '{print $1}' | head -n 1)


function help(){
    echo "Usage: `basename $0` [phase]"
    echo
    echo "This script aims to create new release branches in desired
    set of projects. To describe which set of project, you would
    like to branch, use following arguments:"
    echo
    echo "--libs-clients - to branch clients and libs"
    echo "--cores - to branch cores"
    echo "--tempest - to branch tempest plugins"
    echo "*file* - to branch own list of projects from specified file
    i.e. `basename $0` /tmp/branching_list"
    echo

    exit 0
}


function prepare_rsrc_repo(){
    echo
    echo "~~~ Cloning resources repo or rebasing... ~~~"
    echo

    if [ ! -d "$RSRC_DIR" ]; then
       git clone "$RSRC_REPO_URL" "$RSRC_DIR"
    else
       pushd "$RSRC_DIR"
       git checkout master
       git rebase origin/master
       popd
    fi
}


function generate_project_list(){
    if [[ "$1" =~ "--cores" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list

        PROJECT_LIST="$(rdopkg info -t $MASTER_RELEASE-uc conf:core tags:$MASTER_RELEASE-uc | grep "name: " | sort | sed 's/name: //g')"
        echo "~~~ List of brached projects placed in $BRANCHED_PROJECTS_FILE ~~~"
        echo "$PROJECT_LIST" > "$BRANCHED_PROJECTS_FILE"

        # remove projects which are branched in 1st phase
        sed -i 's/diskimage-builder//' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/dib-utils//' "$BRANCHED_PROJECTS_FILE"
        sed -i '/^$/d' "$BRANCHED_PROJECTS_FILE"

        # adjust project names
        sed -i 's/gnocchi/openstack-gnocchi/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/python-sahara/sahara/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/manila-dashboard/manila-ui/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/magnum-dashboard/magnum-ui/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/ironic-dashboard/ironic-ui/' "$BRANCHED_PROJECTS_FILE"
    elif [[ "$1" =~ "--tempest" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list
        PROJECT_LIST="$(rdopkg info -t $MASTER_RELEASE-uc conf:tempest tags:$MASTER_RELEASE-uc | grep "name: " | sort | sed 's/name: //g')"
        echo "~~~ List of brached projects placed in $BRANCHED_PROJECTS_FILE ~~~"
        echo "$PROJECT_LIST" > "$BRANCHED_PROJECTS_FILE"
    else
            # anditional projects to branch can be specified in file
            BRANCHED_PROJECTS_FILE="$1"
            if [ ! -f "$BRANCHED_PROJECTS_FILE" ]; then
                echo "File you passed doesn't exists!"
                exit 1
            fi
    fi
}


function branching(){
    echo
    echo "~~~ Creating branches in projects... ~~~"
    echo

    cat "$BRANCHED_PROJECTS_FILE" | while IFS= read -r project ; do
        echo "Project name: $project"
        resource_file=$(find "$RSRC_DIR" -name *"$project.yaml")
        if [ ! -n "$resource_file" ] && [[ "$project" =~ "ui" ]]; then
            project_dshb=${project/ui/dashboard}
            resource_file=$(find "$RSRC_DIR" -name *"$project_dshb.yaml")
        fi
        if [ ! -n "$resource_file" ] && [[ "$project" =~ "python-django-horizon" ]]; then
            project="openstack-horizon"
            resource_file=$(find "$RSRC_DIR" -name *"$project.yaml")
        fi
        if [ ! -n "$resource_file" ] && [[ "$project" =~ "tests-tempest" ]]; then
            project=$(echo $project | sed "s/python-\(.*\)-tests-tempest/\1-tempest-plugin/")
            resource_file=$(find "$RSRC_DIR" -name "openstack-$project.yaml")
        fi

        echo "Resource file: $resource_file for project $project"
        if [ -n "$resource_file" ]; then
                distgit=$(rdopkg findpkg "$project" | grep "^distgit:" | awk '{print $2}')
                echo "distgit: $distgit"

                githash=$(git ls-remote "$distgit" refs/heads/rpm-master | awk '{print $1}')
                echo "githash: $githash"

                new_input="$MASTER_RELEASE-rdo: $githash"

                if [ -n "$distgit" ] && [ -n "$githash" ]; then
                    if ! grep -q "$MASTER_RELEASE"-rdo "$resource_file"; then
                        sed -i "/$LATEST_RELEASE-rdo:.*/a \ \ \ \ \ \ \ \ $new_input" "$resource_file"
                    else
                        sed -i "s/$MASTER_RELEASE-rdo.*/$new_input/g" "$resource_file"
                    fi
                else
                    echo "Distgit or githash for $project is not existing or was not found." | tee -a "$LOGS"
                fi

        else
            echo "Resource file for $project is not existing or was not found." | tee -a "$LOGS"
        fi
        echo
    done

    if [ -f "$LOGS" ]; then
        echo
        echo "~~~ SOMETHING WENT WRONG. ~~~"
        echo "~~~ Display log file $LOGS ~~~"
        cat "$LOGS"
    fi
}


#### MAIN ###
# Cleaning log file
rm -rf $LOGS

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    help
fi

if [ "$#" -ne 1 ]; then
    echo
    echo "ERROR: Invalid number of arguments. Printing help."
    help
    exit 1
fi

prepare_rsrc_repo
generate_project_list "$1"
branching
