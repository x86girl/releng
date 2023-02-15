rdo_releases=$(rdopkg info | grep -e "in.*phase" | awk '{print $1}')
export RDO_PENULTIMATE_RELEASE=$(echo $rdo_releases | cut -d" " -f3)
export RDO_LATEST_RELEASE=$(echo $rdo_releases | cut -d" " -f2)
export RDO_MASTER_RELEASE=$(echo $rdo_releases | cut -d" " -f1)
export RDO_NEXT_RELEASE=$(curl --silent https://raw.githubusercontent.com/openstack/releases/master/data/series_status.yaml 2>&1 | grep -e "- name:" | head -n 1 | awk '{print $3}')
# If the next release Openstack name is not yet published
# $RDO_NEXT_RELEASE might be equal to $RDO_MASTER_RELEASE. In
# that case we set RDO_NEXT_RELEASE as empty.
if [ "$RDO_NEXT_RELEASE" == "$RDO_MASTER_RELEASE" ]; then
    export RDO_NEXT_RELEASE=""
fi


# The git repo URL we use
export RDO_RDOINFO_REPO_URL="https://github.com/redhat-openstack/rdoinfo"
export RDO_RELENG_REPO_URL="https://github.com/rdo-infra/releng/"
export RDO_CONFIG_REPO_URL="https://github.com/rdo-infra/review.rdoproject.org-config/"

releng_scripts_path="/releng/scripts/new_release_scripts"
if [ -d "$releng_scripts_path" ]; then
    export PATH="$releng_scripts_path:$PATH"
fi

# As toolbox mount the HOME directory, we have to tell 
# Python to change the default user site-packages dir ($HOME/.local/lib)
# in order to avoid interaction with host system.
# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUSERBASE
export PYTHONUSERBASE="/usr/local"
