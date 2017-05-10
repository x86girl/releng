
import jenkins
import time
import validators

JENKINS_URLS = {
    'rdo': 'https://ci.centos.org',
}


def get_jenkins_client(url, user=None, password=None):
    if url in JENKINS_URLS.keys():
        jenkins_url = JENKINS_URLS[url]
    elif validators.url(url):
        jenkins_url = url
    else:
        msg = "The provided url is not valid."
        return ValueError(msg)
    return jenkins.Jenkins(jenkins_url, username=user, password=password)


def get_job_info(server, job_name):
    return server.get_job_info(job_name)


def get_build_info(server, job_name, job_number):
    return server.get_build_info(job_name, job_number)


def print_build_info(build):
    print "Name: %s" % build['fullDisplayName']
    print "Number: %s" % build['number']
    print "Result: %s" % build['result']
    print "Url: %s" % build['url']


def wait_for_job(server, job_name):
    in_queue = True
    while in_queue:
        time.sleep(5)
        job_info = get_job_info(server, job_name)
        in_queue = job_info['inQueue']
    return job_info


def start_job(server, job_name, parameters={}, token=None):
    parameters['delay'] = '0sec'
    job_info = wait_for_job(server, job_name)
    next = job_info['nextBuildNumber']
    server.build_job(job_name, parameters=parameters, token=token)
    job_info = wait_for_job(server, job_name)
    get_build_info(server, job_name, next)
    return next
