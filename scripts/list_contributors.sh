#!/bin/bash

# Script to list RDO contributors in a period of time
# Usage:
#      list_contributors.sh <initial date> <final date> [--new]
# Dates format must be YYYY-MM-DD
# option '--new' makes to display only new contributors
# examples:
#      list_contributors.sh 2021-05-01 2021-10-15
#      list_contributors.sh 2021-05-01 2021-10-15 --new
#

FROM=$1
TO=$2
NEW=$3

if [ "$NEW" = "--new" ]; then
echo "New contributors in the period $FROM to $TO:"
curl -s "https://review.rdoproject.org/repoxplorer/api/v1/tops/authors/diff?pid=RDO&limit=1000&dfrom=$FROM&dto=$TO&dfromref=2018-04-10&dtoref=$FROM" | jq -r '.[].name'|sort -u 
else
echo -e "The full list of contributors in the period $FROM to $TO:"
curl -s "https://review.rdoproject.org/repoxplorer/api/v1/tops/authors/bycommits?pid=RDO&limit=1000&dfrom=$FROM&dto=$TO"|jq -S -r '.[].name'| sort -u
fi
