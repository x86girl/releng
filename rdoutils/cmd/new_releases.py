
import argparse
import datetime
from rdopkg.actionmods import rdoinfo
from rdoutils import review_utils
from rdoutils import releases_utils


def parse_args():
    parser = argparse.ArgumentParser(description='List new releases tagged in '
                                     'OpenStack projects managed by release '
                                     'project')
    parser.add_argument('-r', '--release', dest='release',
                        default='ocata',
                        help='Project to list open reviews')
    parser.add_argument('-d', '--days', dest='days', default=2, type=int,
                        help='Number of days to list new releases')
    parser.add_argument('-n', '--review-number', dest='number', default=None,
                        help='Review number')
    return parser.parse_args()


def format_time(time):
    tformat = '%Y-%m-%d %H:%M:%S.%f000'
    return datetime.datetime.strptime(time, tformat)


def main():
    args = parse_args()
    if args.number:
        after_fmt = None
    else:
        after = datetime.datetime.now() - datetime.timedelta(days=args.days)
        after_fmt = after.strftime('%Y-%m-%d')
    reviews = review_utils.get_osp_releases_reviews(args.release,
                                                    after=after_fmt,
                                                    number=args.number,
                                                    status='merged')
    inforepo = rdoinfo.get_default_inforepo()
    inforepo.init(force_fetch=True)
    for review in reviews:
        submitted = format_time(review['submitted'])
        review_number = review['_number']
        releases = releases_utils.get_new_releases_review(review)
        for release in releases:
            for repo in release['repos']:
                pkg = inforepo.find_package(repo, strict=True)
                if pkg:
                    name = pkg['name']
                else:
                    name = repo
                print("%s %s %s %s" % (review_number, submitted,
                                       release['version'], name))
