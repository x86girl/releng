
import argparse
import jenkins
import sys

from rdoutils import jenkins_utils


def parse_args():
    parser = argparse.ArgumentParser(description='Start a build for an'
                                     'exiting job in ci.centos.org')
    parser.add_argument('-j', '--job-name', dest='job_name', required=True,
                        help='Name of the job to get status')
    parser.add_argument('-s', '--user', dest='user',
                        help='User authenticated to start the job')
    parser.add_argument('-p', '--password', dest='password',
                        help='User password')
    parser.add_argument('-t', '--token', dest='token',
                        help='Job Token')
    parser.add_argument('-u', '--url', dest='url', default='rdo',
                        type=str, help='URL of jenkins server')
    parser.add_argument('-e', '--parameter', dest='parameters',
                        action='append', type=str,
                        help='URL of jenkins server')
    return parser.parse_args()


def main():
    args = parse_args()
    server = jenkins_utils.get_jenkins_client(args.url, args.user,
                                              args.password)
    try:
        params = {}
        for parm in args.parameters:
            parm_list = parm.split('=')
            if len(parm_list) != 2:
                print "Error in parameter %s: it should be key=value" % parm
                sys.exit(1)
            params[parm_list[0]] = parm_list[1]
        job = jenkins_utils.start_job(server,
                                      args.job_name,
                                      parameters=params,
                                      token=args.token)
        print job
    except jenkins.NotFoundException:
        print("Job %s does not exist" % args.job_name)
