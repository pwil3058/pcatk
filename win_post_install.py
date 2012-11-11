import os
import shutil
import distutils.sysconfig

NAME = 'PaintersColourAssistant'

desktop_dir = get_special_folder_path('CSIDL_DESKTOPDIRECTORY')

for script, descr in [('pcatk_palette.py', 'Palette Planner'), ('pcatk_editor.py', 'Tube Series Editor')]:
    target = os.path.join(distutils.sysconfig.PREFIX, 'Scripts', script)
    link = os.path.join(desktop_dir, descr + '.lnk')
    create_shortcut(target, script, link)
    print 'Created shortcut from {0} to {1}.'.format(link, target)
