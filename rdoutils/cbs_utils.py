import koji

# From https://cbs.centos.org/koji/api
CBS_KOJI_URL = "https://cbs.centos.org/kojihub"


def get_cbs_client():
    return koji.ClientSession(CBS_KOJI_URL)


def list_pkg_names_tagged_in(koji_tag):
    client = get_cbs_client()
    tagged_pkgs = client.listTagged(koji_tag)

    pkg_names = []
    for pkg in tagged_pkgs:
        pkg_names.append(pkg['package_name'])
    return pkg_names
