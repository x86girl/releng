import sys
from ruamel.yaml import YAML
from os.path import exists

all_resources = {}


def get_resource_file_path(local_config, resource):
    return "{}/resources/{}.yaml".format(local_config, resource)


def load_resource(local_config, resource):
    try:
        return all_resources[resource]
    except KeyError:
        pass

    resource_file_path = get_resource_file_path(local_config, resource)
    try:
        with open(resource_file_path, 'rb') as infile:
            yaml = YAML()
            yaml.preserve_quotes = True
            all_resources[resource] = yaml.load(infile)
    except IOError:
        print("The file {} does not exist. "
              "Exiting...".format(resource_file_path))
        sys.exit(1)


def get_repo_data(resource, repo_name):
    try:
        return all_resources[resource]['resources']['repos'][repo_name]
    except KeyError:
        print("Warning: the dependency '{}' is not defined in any "
              "resource files".format(repo_name))


def write_resource_file(local_config, resource, data):
    resource_file_path = get_resource_file_path(local_config, resource)
    with open(resource_file_path, 'w') as outfile:
        yaml = YAML()
        yaml.dump(data, stream=outfile)


def write_resources(local_config):
    for r, r_data in all_resources.items():
        write_resource_file(local_config, r, r_data)


def create_new_branch(resource, repo_name, new_branch, start_point,
                      local_config):
    load_resource(local_config, resource)
    repo_data = get_repo_data(resource, repo_name)
    if repo_data:
        try:
            repo_data['branches'].update({new_branch: start_point})
            return True
        except KeyError:
            print("The repo '{}' does not have 'branches' "
                  "attribute.".format(repo_name))
            return False


def update_dep_default_branch(resource, dep_name, branch_name, local_config):
    load_resource(local_config, resource)
    repo_name = get_dep_reponame(dep_name)
    repo_data = get_repo_data(resource, repo_name)
    if repo_data:
        repo_data['default-branch'] = branch_name


def get_dep_resource_filename(dep_name, local_config):
    resource_filename = "deps-{}".format(dep_name)
    if not exists(get_resource_file_path(local_config, resource_filename)):
        resource_filename = "rdo-deps"
    return resource_filename


def get_dep_reponame(dep_name):
    return "deps/{}".format(dep_name)


def branch_dependency(dep_name, new_branch, start_point, local_config):
    resource_filename = get_dep_resource_filename(dep_name, local_config)
    repo_name = get_dep_reponame(dep_name)
    is_branched = create_new_branch(resource_filename, repo_name, new_branch,
                                    start_point, local_config)
    if is_branched:
        update_dep_default_branch(resource_filename, dep_name, new_branch,
                                  local_config)


def branch_dependencies_from_file(deps_file, new_branch, start_point,
                                  local_config):
    try:
        f = open(deps_file, "r")
        deps = f.readlines()
    except IOError:
        print("Could not open file '{}'".format(deps_file))
        return

    for dep_name in deps:
        branch_dependency(dep_name.strip(), new_branch, start_point,
                          local_config)
    write_resources(local_config)
