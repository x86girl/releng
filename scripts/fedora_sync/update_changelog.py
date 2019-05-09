from rdopkg.utils.specfile import Spec

import sys

file_path = sys.argv[1]
chlog_name = sys.argv[2]
chlog_mail = sys.argv[3]

specfile = Spec(fn=file_path)
new_version = specfile.get_vr().split('-')[0].split(':')[-1]
chnlog_text = ("Update to upstream version %s" % new_version)
specfile.new_changelog_entry(chlog_name, chlog_mail, changes=[chnlog_text])
specfile.save()
