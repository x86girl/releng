import argparse
import pandas
from rdoutils import review_utils
import urllib.error


def parse_args():
    parser = argparse.ArgumentParser(description='Generate raport of current'
                                     ' package building failures.')
    parser.add_argument('-r', '--release', dest='release', action='append',
                        required=False,
                        help='Define releases for which report should be'
                             ' created. If empty, all currently maintained'
                             ' releases will be used.')
    parser.add_argument('-o', '--report_file', dest='report_file',
                        required=False,
                        help='File to store generated report. If empty, report'
                             ' will be displayed to stdout.')
    return parser.parse_args()


def get_ftbfs_failures(release):
    """
    This function is parsing csv report to look for any occurenence
    of FTBFS and store this information
    """
    url = "https://trunk.rdoproject.org/%s/status_report.csv" % release
    print("INFO: Analysing report from URL: ", url)

    try:
        df_data = pandas.read_csv(url, index_col='Project')
    except urllib.error.HTTPError as e:
        print("Result: ", e.code, e.reason)
        print("Specified report url", url, "does not exists.")
        return

    df_data.drop(["Extended Sha", "Packages"], axis=1, inplace=True)
    failed_reviews = df_data[df_data["Status"] == "FAILED"]
    if not failed_reviews.empty:
        for project in failed_reviews.index:
            failed_reviews = failed_reviews.assign(Release=release)
        return failed_reviews


def expand_report(report_df):
    """
    This function is expanding basic report dataframe, which contains list of
    currently failing packages with columns with log URL, date of FTBFS and
    link to gerrit review (if exists). Also it does some clean up of unneeded
    columns.
    """

    if report_df.empty:
        print("INFO: Current FTBFS report has no entries.")
        return report_df

    report_df["Review"] = None
    report_df["Logs"] = None
    # TODO: enable source commit hash
    # report["Commit"] = None
    report_df["Date of FTBFS"] = None

    report_df.reset_index(inplace=True)

    for index in report_df.index:
        component = report_df["Release"][index]
        if "centos7-train" not in component:
            component += "/component/" + report_df['Component'][index]
        rpmbuild_log = "https://trunk.rdoproject.org/" \
                       + component + "/" \
                       + report_df['Source Sha'][index][:2] + "/" \
                       + report_df['Source Sha'][index][2:4] + "/" \
                       + report_df['Source Sha'][index] + "_" \
                       + report_df['Dist Sha'][index][:8] + "/rpmbuild.log"

        ftbfs_date = pandas.to_datetime(report_df['Timestamp'][index],
                                        unit='s')
        ftbfs_review = find_ftbfs_reviews(report_df["Project"]
                                          [index].split("-")[1],
                                          report_df["Release"]
                                          [index].split("-")[1],
                                          "open")

        report_df.loc[index, "Logs"] = rpmbuild_log
        report_df.loc[index, "Date of FTBFS"] = ftbfs_date
        report_df.loc[index, "Review"] = ftbfs_review

    report_df.drop(["Timestamp", "Source Sha", "Dist Sha"],
                   axis=1, inplace=True)
    report_df.set_index("Project", inplace=True)

    return report_df


def find_ftbfs_reviews(project, branch, status):
    """
    This function is calling gerrit API to list all current
    FTBFS reviews, with specified project, branch and status.
    """
    client = review_utils.get_gerrit_client('rdo')
    gerrit_url = 'https://review.rdoproject.org/r/#/c/'

    if branch and "master" in branch:
        branch = "rpm-master"
    elif branch:
        branch = branch + "-rdo"

    reviews = review_utils.get_reviews_project(client, project,
                                               branch=branch,
                                               status=status,
                                               intopic="FTBFS")
    if reviews:
        latest_review = 0
        for review in reviews[::-1]:
            if latest_review < review['_number']:
                latest_review = review['_number']

        return gerrit_url + str(latest_review)


def main():
    releases = []
    ftbfs_failures_df = pandas.DataFrame()

    args = parse_args()

    if args.release is None:
        releases = ["centos8-wallaby", "centos8-xena", "centos8-yoga",
                    "centos9-wallaby", "centos9-xena", "centos9-yoga",
                    "centos9-zed", "centos9-antelope", "centos9-bobcat",
                    "centos9-caracal", "centos9-master", "centos9-master-head"]
    else:
        releases = args.release

    for release in releases:
        ftbfs_failures_df = pandas.concat([ftbfs_failures_df,
                                           get_ftbfs_failures(release)])

    if args.report_file is None:
        print(expand_report(ftbfs_failures_df))
    elif args.report_file is not None and ftbfs_failures_df.empty:
        with open(args.report_file, 'w'):
            pass
    else:
        print("INFO: Report file specified, printing to", args.report_file)
        expand_report(ftbfs_failures_df).to_csv(args.report_file, mode='w',
                                                sep=',', index=True)
