import sys
from rdoutils import rdoinfo

if len(sys.argv) not in [5, 6]:
    print("usage: update-tag.py <rdoinfo location> <tag> <package> \
          <source-branch value>")
    sys.exit(1)

RDOINFO_DIR = sys.argv[1]
TAG = sys.argv[2]
PACKAGE = sys.argv[3]
PIN = sys.argv[4]
MODE = sys.argv[5] or "pin"

if MODE == "pin":
    print("Updating tag: %s for project: %s to %s" % (TAG, PACKAGE, PIN))
    rdoinfo.update_tag('tags', PACKAGE, TAG, {'source-branch': PIN},
                       local_dir=RDOINFO_DIR)
else:
    print("Unsetting tag: %s for project: %s" % (TAG, PACKAGE))
    rdoinfo.update_tag('tags', PACKAGE, TAG, None, local_dir=RDOINFO_DIR)
