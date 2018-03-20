
import argparse
from rdoutils import review_utils


def parse_args():
    parser = argparse.ArgumentParser(description='List existing reviews for '
                                     'project')
    parser.add_argument('-p', '--project', dest='project',
                        help='Project to list open reviews')
    parser.add_argument('-s', '--status', dest='status', default='open',
                        help='Status of the reviews to list')
    parser.add_argument('-b', '--branch', dest='branch', default=None,
                        help='Branch of the reviews to list')
    return parser.parse_args()


def main():
    args = parse_args()
    client = review_utils.get_gerrit_client('rdo')
    gerrit_url = 'https://review.rdoproject.org/r/#/c/'
    reviews = review_utils.get_reviews_project(client, args.project,
                                               status=args.status,
                                               branch=args.branch)
    for review in reviews:
        print("%s %s %s %s %s %s" % (review['status'], review['_number'],
                                     review['project'], review['subject'],
                                     review['branch'],
                                     gerrit_url+str(review['_number'])))
