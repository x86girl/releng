import json
import re
import requests
import yaml


def get_release_file(commit, path):
    url = ("https://raw.githubusercontent.com/openstack/releases/%s/%s" %
           (commit, path))
    release = requests.get(url)
    if release.status_code == 200:
        return release.text
    else:
        return None


def get_release_info(release_content):
    deliverable = yaml.safe_load(release_content)
    if 'releases' not in deliverable.keys():
        return None
    releases = deliverable['releases']
    latest_release = releases[-1]
    if 'projects' not in latest_release.keys():
        return None
    projects = latest_release['projects']
    repos = [p['repo'] for p in projects]
    release = {
        'name': deliverable['team'],
        'version': latest_release['version'],
        'repos': repos,
    }
    return release


def get_new_releases_review(review):
    new_releases = []
    cur_rev = review['current_revision']
    cur_rev_info = review['revisions'][cur_rev]
    parent_rev = cur_rev_info['commit']['parents'][0]['commit']
    files = cur_rev_info['files']
    for mod_file in files.keys():
        re_release = re.compile('deliverables/(.*)/.*')
        release = re.search(re_release, mod_file).group(1)
        file_def = files[mod_file]
        if 'status' in file_def.keys() and file_def['status'] == 'D':
            continue
        new_release_f = get_release_file(cur_rev, mod_file)
        new_release = get_release_info(new_release_f)
        if not new_release:
            continue
        new_release['release'] = release
        parent_release_f = get_release_file(parent_rev, mod_file)
        if parent_release_f is None:
            new_releases.append(new_release)
        else:
            parent_release = get_release_info(parent_release_f)
            if parent_release is None:
                new_releases.append(new_release)
            else:
                if new_release['version'] != parent_release['version']:
                    new_releases.append(new_release)
    return new_releases


def refined_get(url, user, password):
    result = requests.get(url, auth=(user, password))
    if result.status_code == 200:
        result_json = json.loads(result.text)
        return result_json
    else:
        return None


def get_files_release(release, user, password, only_branched=False):
    if only_branched:
        base_url = ("https://api.github.com/search/code?q=stable/%spath"
                    ":deliverables/%s+repo:openstack/releases" %
                    (release, release))
    else:
        base_url = ("https://api.github.com/search/code?q=path:deliverables"
                    "/%s+repo:openstack/releases" % release)
    result = refined_get(base_url, user, password)
    if result:
        files = []
        page = 1
        while len(files) < result['total_count']:
            url = "%s&page=%s" % (base_url, page)
            result_page = refined_get(url, user, password)
            files_page = [item['name'] for item in result_page['items']]
            files = files + files_page
            page += 1
        return files
