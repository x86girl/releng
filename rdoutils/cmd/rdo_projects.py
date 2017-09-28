
import argparse
from rdoutils import review_utils
from rdoutils import rdoinfo


def parse_args():
    parser = argparse.ArgumentParser(description='List projects in RDO')
    parser.add_argument('-b', '--branch', dest='branch', default=None,
                        help='List only projects having this branch')
    parser.add_argument('-n', '--not-branch', dest='notbranch', default=None,
                        help='List only projects not having this branch')
    parser.add_argument('-r', '--release', dest='release', default=None,
                        help='List projects for this release in rdoinfo')
    parser.add_argument('-m', '--missing-in-tag', dest='missing', default=None,
                        help='List missing projects from specified CBS tag'
                             'for the release specified in -r')
    return parser.parse_args()


def main():
    args = parse_args()
    client = review_utils.get_gerrit_client('rdo')
    if args.release:
        dist_in_rel = rdoinfo.get_projects_distgit(tag=args.release)
    else:
        dist_in_rel = None
    if args.notbranch:
        projects = {}
        all_projects = review_utils.get_rdo_projects(client)
        in_branch = review_utils.get_rdo_projects(client, b=args.notbranch)
        for project in [p for p in all_projects.keys()
                        if p not in in_branch.keys()]:
            projects[project] = all_projects[project]
    else:
        projects = review_utils.get_rdo_projects(client, b=args.branch)
    projects_gerrit = projects.keys()
    if dist_in_rel:
        if args.missing:
            cbs_tag = args.missing
            projects_cbs = rdoinfo.get_projects_distgit(buildsys_tag=cbs_tag)
            filtered_rel = list(set(dist_in_rel) - set(projects_cbs))
        else:
            filtered_rel = list(set(projects_gerrit) & set(dist_in_rel))
    else:
        filtered_rel = projects_gerrit
    for proj in filtered_rel:
        print(proj)
