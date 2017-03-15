# RDO Release Enginnering tools

This repo contains some utilities used in release management tasks in RDO project.

Following executable are provided in this repository:

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

## TODO

1. Add custom location for rdoinfo in rdoutils/rdoinfo.py
2. Manage independent reviews in rdo_release_review
3. Add some unit tests

