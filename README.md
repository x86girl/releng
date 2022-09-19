# RDO Release Enginnering tools

This repo contains some utilities used in release management tasks in RDO project.

Following executable are provided in this repository:

- **check_dependants**: list of packages wich depends on a specific source package name
- **new_releases**: list new releases tagged in OpenStack projects managed by release project
- **rdo_project**: list projects in RDO for releases and check branches status
- **reviews_rdo_project**: list existing reviews for projects in review.rdoproject.org
- **rdo_release_review**: automatically creates reviews to build new stable builds when
new releases are tagged upstream.

Directory `scripts` contains some bash scripts used for common tasks.

## Requirements

1. Install requirements listed in requirements.txt, see notes about binary requirements
2. Clone rdoinfo into ~/rdoinfo directory
3. Copy ssh private key used in review.rdoproject.org under ~/.ssh/
4. Configure .gitconfig to use the desired user when creating reviews (rdo_release_review)
5. ssh review.rdoproject.org to add server key to known_hosts

**Not about using virtualenv:** rpm python module is not delivered via pypi so, if you plan
to use virtualenv to run rdo_release_review, add '--system-site-packages' option when creating
the virtualenv to use rpm module from the system.

## Usage examples:-

**rdo_release_review**
-  To see available options for running the script, run:-
```
   rdo_release_review --help
```

-  To run rdo_release_review against a upstream change, run:-
```
   # Replace <...> in below commands with a valid full or short commit hash, change-id or review id
   rdo_release_review -u rdo-trunk -c RDO -e dev@lists.rdoproject.org -r newton -n <reference review> --dry-run
   # For strict search for a commit or change-id, run:-
   rdo_release_review -u rdo-trunk -c RDO -e dev@lists.rdoproject.org -r newton -n commit:<commit-id> --dry-run
   rdo_release_review -u rdo-trunk -c RDO -e dev@lists.rdoproject.org -r newton -n change:<change-id> --dry-run
```

-  To run rdo_release_review against rdoinfo pin, run:-
```
   rdo_release_review -u rdo-trunk -c RDO -e dev@lists.rdoproject.org -r pike -p /home/$USER/rdoinfo --dry-run
```

-  Don't pass --dry-run if you want the script to send reviews to https://review.rdoproject.org

**rdo_projects**
-  To see available options for running the script, run:-
```
   rdo_projects --help
```

- To list distgit projects which are available in `<release>`, but are **NOT** yet branched (i.e `<release>-rdo`), run:-
```
  rdo_projects -r zed -n zed-rdo
```

- To list distgit projects which have the `<release>-rdo` branch, but are not yet tag in CBS `cloud*-openstack-<release>-candidate` tag, run:-
```
  rdo_projects -r zed -b zed-rdo -m cloud9s-openstack-zed-candidate
  # Note: this is useful when preparing new RDO release, you can spot the projects that are branched but do not have a build tagged yet.
```


## TODO

1. Add custom location for rdoinfo in rdoutils/rdoinfo.py
2. Manage independent reviews in rdo_release_review
3. Add some unit tests

