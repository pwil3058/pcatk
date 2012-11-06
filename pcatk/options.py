### Copyright: Peter Williams (2012) - All rights reserved
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''Manage configurable options'''

import os
import collections

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from pcatk import i18n

_USER_CONFIG_DIR_PATH = os.path.expanduser('~/.' + i18n.APP_NAME)
_USER_CFG_FILE_PATH = os.path.join(_USER_CONFIG_DIR_PATH, 'options.cfg')

def get_user_config_dir():
    return _USER_CONFIG_DIR_PATH

if not os.path.exists(_USER_CONFIG_DIR_PATH):
    os.mkdir(_USER_CONFIG_DIR_PATH, 0o775)

USER_OPTIONS = configparser.SafeConfigParser()

Result = collections.namedtuple('Result', ['sucessful', 'why_not'])
OK = Result(True, None)

def load_user_options():
    global USER_OPTIONS
    USER_OPTIONS = configparser.SafeConfigParser()
    try:
        USER_OPTIONS.read(_USER_CFG_FILE_PATH)
    except configparser.ParsingError as edata:
        return Result(False, _('Error reading user options: {0}\n').format(str(edata)))
    return OK
# END_DEF: load_user_options

def reload_user_options():
    global USER_OPTIONS
    new_version = configparser.SafeConfigParser()
    try:
        new_version.read(_USER_CFG_FILE_PATH)
    except configparser.ParsingError as edata:
        return Result(False, _('Error reading user options: {0}\n').format(str(edata)))
    USER_OPTIONS = new_version
    return OK
# END_DEF: reload_user_options

class DuplicateDefn(Exception): pass

Defn = collections.namedtuple('Defn', ['str_to_val', 'default', 'help'])

DEFINITIONS = {}

def define(section, oname, odefn):
    if not section in DEFINITIONS:
        DEFINITIONS[section] = {oname: odefn,}
    elif oname in DEFINITIONS[section]:
        raise DuplicateDefn('{0}:{1} already defined'.format(section, oname))
    else:
        DEFINITIONS[section][oname] = odefn
# END_DEF: define

def str_to_bool(string):
    lowstr = string.lower()
    if lowstr in ['true', 'yes', 'on', '1']:
        return True
    elif lowstr in ['false', 'no', 'off', '0']:
        return False
    else:
        return None
# END_DEF: str_to_bool

def get(section, oname):
    # This should cause an exception if section:oname is not known
    # which is what we want
    str_to_val = DEFINITIONS[section][oname].str_to_val
    value = None
    if USER_OPTIONS.has_option(section, oname):
        value = str_to_val(USER_OPTIONS.get(section, oname))
    return value if value is not None else DEFINITIONS[section][oname].default
# END_DEF: get

def set(section, oname, val):
    # This should cause an exception if section:oname is not known
    # which is what we want
    if not USER_OPTIONS.has_section(section):
        if DEFINITIONS[section][oname]:
            USER_OPTIONS.add_section(section)
        else:
            raise LookupError('{0}:{1}'.format(section, oname))
    USER_OPTIONS.set(section, oname, val)
    USER_OPTIONS.write(open(_USER_CFG_FILE_PATH, 'w'))
# END_DEF: set

def get_help(section, oname):
    # This should cause an exception if section:oname is not known
    # which is what we want
    str_to_val = DEFINITIONS[section][oname].str_to_val
    value = None
    if USER_OPTIONS.has_option(section, oname):
        value = str_to_val(USER_OPTIONS.get(section, oname))
    return value if value is not None else DEFINITIONS[section][oname].default
# END_DEF: get_help

define('user', 'name', Defn(str, None, _('User\'s display name e.g. Fred Bloggs')))
define('user', 'email', Defn(str, None, _('User\'s email address e.g. fred@bloggs.com')))
define('colour_wheel', 'red_to_yellow_clockwise', Defn(bool, False, _('Direction around colour wheel from red to yellow.')))

load_user_options()
