#!/bin/bash
set -e


REALPATH=$(realpath "$0")
DIRNAME=$(dirname "$REALPATH")
WORKDIR=/tmp/"$(basename -s .sh $0)"
VIRTUAL_ENV=$WORKDIR/.venv
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
    echo "--deps - to branch the dependencies"
    echo "--puppet - to branch the Openstack puppet modules"
    echo "--non-os-puppet - to branch the non Openstack puppet modules"
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


function prepare_virtualenv(){
    if [ ! -d $VIRTUAL_ENV ]; then
        echo "~~~ Creating a virtual environment... ~~~"
        virtualenv -p /usr/bin/python3 $VIRTUAL_ENV >/dev/null
    fi
    source $VIRTUAL_ENV/bin/activate >/dev/null
    echo "~~~ Installing the required dependencies... ~~~"
    python3 -m pip install --upgrade pip >/dev/null
    pip install -q $DIRNAME/../..
}


function generate_project_list(){
    if [[ "$1" =~ "--cores" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list

        PROJECT_LIST="$(rdopkg info -t $MASTER_RELEASE-uc conf:core tags:$MASTER_RELEASE-uc | grep "name: " | sort | sed 's/name: //g')"
        echo "~~~ List of brached projects placed in $BRANCHED_PROJECTS_FILE ~~~"
        echo "$PROJECT_LIST" > "$BRANCHED_PROJECTS_FILE"

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
    elif [[ "$1" =~ "--libs-clients" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list
        PROJECT_LIST_LIB="$(rdopkg info -t $MASTER_RELEASE-uc conf:lib tags:$MASTER_RELEASE-uc | grep "name: " | sort | sed 's/name: //g')"
        PROJECT_LIST_CLIENT="$(rdopkg info -t $MASTER_RELEASE-uc conf:client tags:$MASTER_RELEASE-uc | grep "name: " | sort | sed 's/name: //g')"
        echo "~~~ List of brached projects placed in $BRANCHED_PROJECTS_FILE ~~~"
        echo "$PROJECT_LIST_LIB" > "$BRANCHED_PROJECTS_FILE"
        echo "$PROJECT_LIST_CLIENT" >> "$BRANCHED_PROJECTS_FILE"
        sed -i 's/glance-store/glance_store/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/kuryr-lib/kuryr/' "$BRANCHED_PROJECTS_FILE"
        sed -i 's/python-//' "$BRANCHED_PROJECTS_FILE"
    elif [[ "$1" =~ "--deps" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list
        rdopkg info conf:.-*dependency | grep -e "name:" | sort | awk '{print $2}' > $BRANCHED_PROJECTS_FILE
    elif [[ "$1" =~ "--puppet" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list
        rdopkg info conf:rpmfactory-puppet tags:$LATEST_RELEASE upstream:https://opendev.org/ | grep -e "name:" | sort | awk '{print $2}' > $BRANCHED_PROJECTS_FILE
    elif [[ "$1" =~ "--non-os-puppet" ]]; then
        BRANCHED_PROJECTS_FILE="$WORKDIR"/"$(echo $1 | tr -d '-')"_branching_list
        rdopkg info conf:rpmfactory-puppet tags:$LATEST_RELEASE upstream:~https://opendev.org/ | grep -e "name:" | sort | awk '{print $2}' > $BRANCHED_PROJECTS_FILE
    else
            # anditional projects to branch can be specified in file
            BRANCHED_PROJECTS_FILE="$1"
            if [ ! -f "$BRANCHED_PROJECTS_FILE" ]; then
                echo "File you passed doesn't exists!"
                exit 1
            fi
    fi
}


function branching_using_python(){
    echo
    echo "~~~ Creating branches in projects... ~~~"
    echo

    pushd "$WORKDIR"
    if [[ "$1" =~ "--deps" ]]; then
        python3 -c "from rdoutils import resources_utils as ru ; ru.branch_dependencies_from_file('${BRANCHED_PROJECTS_FILE}', 'c9s-${MASTER_RELEASE}-rdo', 'c9s-${LATEST_RELEASE}-rdo', 'config')"
    elif [[ "$1" =~ "puppet" ]]; then
        cat "$BRANCHED_PROJECTS_FILE" | while IFS= read -r project ; do
            python3 -c "from rdoutils import resources_utils as ru ; ru.branch_puppet_module('${project}', '${LATEST_RELEASE}-rdo', 'config')"
        done
    fi
    rm -f $BRANCHED_PROJECTS_FILE
    popd
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
        if [ ! -n "$resource_file" ] && [[ "$project" = "openstack-rally-plugins" ]]; then
            resource_file=$(find "$RSRC_DIR" -name "openstack-rally.yaml")
        fi
        if [ ! -n "$resource_file" ] && [[ "$project" = "openstack-rally" ]]; then
            resource_file=$(find "$RSRC_DIR" -name "openstack-rally-openstack.yaml")
        fi
        if [ ! -n "$resource_file" ] && [[ "$project" = "golang-github-openstack-k8s-operators-os-diff" ]]; then
            resource_file=$(find "$RSRC_DIR" -name "openstack-os-diff.yaml")
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
prepare_virtualenv
generate_project_list "$1"
if [[ "$1" =~ "--deps" ]] || [[ "$1" =~ "puppet" ]]; then
    branching_using_python "$1"
else
    branching
fi
