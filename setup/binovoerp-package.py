#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import print_function
import logging
import optparse
import os
import shutil
import subprocess
import tempfile
import time
import traceback
import sys
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
from glob import glob
from os.path import abspath, dirname, join
import re


# ----------------------------------------------------------
# Utils
# ----------------------------------------------------------
exec(open(join(dirname(__file__), '..', 'odoo', 'release.py'), 'rb').read())
version = version.split('-')[0].replace('saas~', '')
docker_version = version.replace('+', '')
timestamp = time.strftime("%Y%m%d", time.gmtime())
PUBLISH_DIRS = {
    'debian': 'deb'
}
ADDONS_NOT_TO_PUBLISH = [
]


def move_glob(source, wildcards, destination):
    """Move files matched by wildcards from source to destination
    wildcards can be a single string wildcard like '*.deb' or a list of wildcards
    """
    if not os.path.isdir(destination):
        raise BaseException("Destination \"%s\" is not a directory" % destination)
    if isinstance(wildcards, str):
        wildcards = [wildcards]
    for wc in wildcards:
        for file_path in glob(os.path.join(source, wc)):
            shutil.move(file_path, destination)


def mkdir(d):
    if not os.path.isdir(d):
        os.makedirs(d)


def publish(o, type, extensions):
    def _publish(o, release):
        build_path = os.path.join(o.build_dir, release)
        filename = release.split(os.path.sep)[-1]
        release_dir = PUBLISH_DIRS[type]
        release_path = join(o.pub, release_dir, filename)
        os.renames(build_path, release_path)
        # Latest/symlink handler
        release_abspath = abspath(release_path)
        if o.version:
            latest_abspath = release_abspath.replace(o.version, '%s.latest' % version)
        else:
            latest_abspath = release_abspath.replace(timestamp, 'latest')
        if os.path.islink(latest_abspath):
            os.unlink(latest_abspath)
        os.symlink(release_abspath, latest_abspath)
        return release_path

    published = []
    for extension in extensions:
        release = glob("%s/odoo_*.%s" % (o.build_dir, extension))
        if release:
            published.append(_publish(o, release[0]))
    return published


# ----------------------------------------------------------
# Stage: building
# ----------------------------------------------------------
def _prepare_build_dir(o):
    cmd = ['rsync', '-a', '--exclude', '.git', '--exclude', '*.pyc', '--exclude', '*.pyo', '--exclude', 'setup/win32']
    subprocess.run(cmd + ['%s/' % o.odoo_dir, o.build_dir])
    for addon_path in glob(join(o.build_dir, 'addons/*')):
        if addon_path.split(os.path.sep)[-1] not in ADDONS_NOT_TO_PUBLISH:
            shutil.move(addon_path, join(o.build_dir, 'odoo/addons'))


def build_deb(o):
    # Append timestamp to version for the .dsc to refer the right .tar.gz
    changelog_version = "%s.%s" % (version, timestamp)
    if o.version:
        regex = "^%s[.][0-9]{4}[0-9]{2}[0-9]{2}([.][0-9]+)?$" % version
        if not re.match(regex, o.version):
            raise Exception(
                "The provided version %s does not comply with the naming convention.\n"
                "<odoo version>.<today timestamp>[.<number of today releases>]\n"
                "e.g.: %s\n"
                "e.g.: %s.1\n" %
                (o.version, changelog_version, changelog_version))
        changelog_version = o.version
    cmd = ['sed', '-i', '1s/^.*$/odoo (%s) stable; urgency=low/' % changelog_version, 'debian/changelog']
    subprocess.call(cmd, cwd=o.build_dir)
    status_code = subprocess.call(['dpkg-buildpackage', '-rfakeroot', '-uc', '-us'], cwd=o.build_dir)
    if 0 != status_code:
        raise Exception("An error ocurred while building package %s" % o.package_name)
    # As the packages are built in the parent of the buildir, we move them back to build_dir
    build_dir_parent = "%s/../" % o.build_dir
    wildcards = ["odoo_%s" % wc for wc in ('*.dsc', '*_amd64.changes', '*.tar.gz', '*.tar.xz')]
    move_glob(build_dir_parent, wildcards, o.build_dir)


# ---------------------------------------------------------
# Generates Packages, Sources and Release files of debian package
# ---------------------------------------------------------
def gen_deb_package(o, published_files):
    # Executes command to produce file_name in path, and moves it to o.pub/deb
    def _gen_file(o, command, file_name, path):
        cur_tmp_file_path = os.path.join(path, file_name)
        with open(cur_tmp_file_path, 'w') as out:
            subprocess.call(command, stdout=out, cwd=path)
        shutil.copy(cur_tmp_file_path, os.path.join(o.pub, 'deb', file_name))

    # Copy files to a temp directory (required because the working directory must contain only the
    # files of the last release)
    temp_path = tempfile.mkdtemp(suffix='debPackages')
    for pub_file_path in published_files:
        shutil.copy(pub_file_path, temp_path)

    commands = [
        (['dpkg-scanpackages', '.'], "Packages"),  # Generate Packages file
        (['dpkg-scansources', '.'], "Sources"),  # Generate Sources file
        (['apt-ftparchive', 'release', '.'], "Release")  # Generate Release file
    ]
    # Generate files
    for command in commands:
        _gen_file(o, command[0], command[-1], temp_path)
    # Remove temp directory
    shutil.rmtree(temp_path)


# ----------------------------------------------------------
# Options and Main
# ----------------------------------------------------------
def options():
    op = optparse.OptionParser()
    root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    build_dir = "%s-%s" % (root, timestamp)

    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    op.add_option("", "--version", default=None, help="override default calculated version")
    op.add_option("-b", "--build-dir", default=build_dir, help="build directory (%default)", metavar="DIR")
    op.add_option("-p", "--pub", default=None, help="pub directory (%default)", metavar="DIR")

    op.add_option("", "--build-deb", action="store_true", help="don't build the debian package")
    op.add_option("", "--no-remove", action="store_true", help="don't remove build dir")
    op.add_option(
        "", "--logging", action="store", type="choice", choices=list(log_levels.keys()), default="info",
        help="Logging level")

    (o, args) = op.parse_args()
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %I:%M:%S', level=log_levels[o.logging])
    # derive other options
    o.odoo_dir = root
    o.pkg = join(o.build_dir, 'pkg')
    o.work = join(o.build_dir, 'openerp-%s' % version)
    o.work_addons = join(o.work, 'odoo', 'addons')

    return o


def main():
    errors = 0
    o = options()
    try:
        _prepare_build_dir(o)
        if o.build_deb:
            build_deb(o)
            try:
                published_files = publish(o, 'debian', ['deb', 'dsc', 'changes', 'tar.xz'])
                gen_deb_package(o, published_files)
            except Exception as e:
                errors += 1
                logging.error("Won't publish the deb release.\n Exception: %s" % str(e))
                traceback.print_exc()
    except Exception as e:
        errors += 1
        logging.error('Something bad happened ! : %s' % e)
        traceback.print_exc()
    finally:
        if o.no_remove:
            logging.info("Build dir \"%s\" not removed" % o.build_dir)
        else:
            shutil.rmtree(o.build_dir)
            logging.info('Build dir %s removed' % o.build_dir)
        sys.exit(errors)


if __name__ == '__main__':
    main()
