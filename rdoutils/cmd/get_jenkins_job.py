
import argparse
import jenkins
from rdoutils import jenkins_utils


def parse_args():
    parser = argparse.ArgumentParser(description='Get status of jenkins job'
                                     'running in ci.centos.org')
    parser.add_argument('-j', '--job-name', dest='job_name', required=True,
                        help='Name of the job to get status')
    parser.add_argument('-n', '--number', dest='number', type=int,
                        required=True,
                        help='Build number to get status')
    parser.add_argument('-r', '--result-only', dest='result_only',
                        action='store_true', default=False,
                        help='Show only result of the job ')
    parser.add_argument('-u', '--url', dest='url',
                        type=str, default='rdo',
                        help='URL of jenkins server')
    return parser.parse_args()


def main():
    args = parse_args()
    server = jenkins_utils.get_jenkins_client(args.url)
    try:
        job = jenkins_utils.get_build_info(server, args.job_name, args.number)
        if args.result_only:
            print(job['result'])
        else:
            jenkins_utils.print_build_info(job)
    except jenkins.NotFoundException:
        print("Job %s number %s does not exist" % (args.job_name, args.number))
