
import requests
import validators

from pygerrit.rest import GerritRestAPI
from requests.auth import HTTPBasicAuth

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

GERRIT_URLS = {
    'rdo': 'https://review.rdoproject.org/api',
    'osp': 'https://review.openstack.org/',
}

QUERY_PARMS = "&o=CURRENT_REVISION&o=ALL_FILES&o=CURRENT_COMMIT"


def get_gerrit_client(url, user=None, password=None):
    if GERRIT_URLS[url]:
        gerrit_url = GERRIT_URLS[url]
    elif validators.url(url):
        gerrit_url = url
    else:
        msg = "The provided url is not valid."
        return ValueError(msg)
    if user and password:
        return GerritRestAPI(url=gerrit_url,
                             auth=HTTPBasicAuth(user, password),
                             verify=False)
    else:
        return GerritRestAPI(url=gerrit_url, verify=False)


def get_osp_releases_reviews(release, after, status='merged'):
    client = get_gerrit_client('osp')
    rev_url = ("/changes/?q=status:%s+project:openstack/releases+file:"
               "deliverables+file:%s+after:%s%s" %
               (status, release, after, QUERY_PARMS))
    reviews = client.get(rev_url)
    return(reviews)


def get_review(review):
    client = get_gerrit_client('osp')
    review = client.get("/changes/?q=%s%s" % (review, QUERY_PARMS))
    return(review)


def get_reviews_project(client, project, **kwargs):
    url = "/changes/?q=project:\"^.*%s.*\"" % project
    for key, value in kwargs.iteritems():
        if value:
            url = "%s+%s:%s" % (url, key, value)
    return client.get(url)


def get_rdo_projects(client, **kwargs):
    url = '/projects/?r=(puppet|openstack)%2F.*distgit'
    for key, value in kwargs.iteritems():
        if value:
            url = "%s&%s=%s" % (url, key, value)
    projects = client.get(url)
    return projects
