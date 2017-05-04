#
# (c) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import os
import re
import sys

from setuptools.command import sdist


# Get requirements from the first file that exists
def get_reqs_from_files(requirements_files):
    for requirements_file in requirements_files:
        if os.path.exists(requirements_file):
            with open(requirements_file, 'r') as fil:
                return fil.read().split('\n')
    return []


def parse_requirements(requirements_files=['tools/pip-requires']):
    requirements = []
    for line in get_reqs_from_files(requirements_files):
        # For the requirements list, we need to inject only the portion
        # after egg= so that distutils knows the package it's looking for
        # such as:
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1',
                                line))
        # such as:
        elif re.match(r'\s*https?:', line):
            requirements.append(re.sub(r'\s*https?:.*#egg=(.*)$', r'\1',
                line))
        # -f lines are for index locations, and don't get used here
        elif re.match(r'\s*-f\s+', line):
            pass
        # argparse is part of the standard library starting with 2.7
        # adding it to the requirements list screws distro installs
        elif line == 'argparse' and sys.version_info >= (2, 7):
            pass
        else:
            requirements.append(line)

    return requirements


def parse_dependency_links(requirements_files=['requirements.txt',
                                               'tools/pip-requires']):
    dependency_links = []
    # dependency_links inject alternate locations to find packages listed
    # in requirements
    for line in get_reqs_from_files(requirements_files):
        # skip comments and blank lines
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        # lines with -e or -f need the whole line, minus the flag
        if re.match(r'\s*-[ef]\s+', line):
            dependency_links.append(re.sub(r'\s*-[ef]\s+', '', line))
        # lines that are only urls can go in unmolested
        elif re.match(r'\s*https?:', line):
            dependency_links.append(line)
    return dependency_links


def get_cmdclass():
    """Return dict of commands to run from setup.py."""

    cmdclass = dict()

    def _find_modules(arg, dirname, files):
        for filename in files:
            if filename.endswith('.py') and filename != '__init__.py':
                arg["%s.%s" % (dirname.replace('/', '.'),
                               filename[:-3])] = True

    class LocalSDist(sdist.sdist):
        """Builds the ChangeLog and Authors files from VC first."""

        def run(self):
            sdist.sdist.run(self)

    cmdclass['sdist'] = LocalSDist

    # If Sphinx is installed on the box running setup.py,
    # enable setup.py to build the documentation, otherwise,
    # just ignore it
    try:
        from sphinx.setup_command import BuildDoc

        class LocalBuildDoc(BuildDoc):

            builders = ['html', 'man']

            def generate_autoindex(self):
                print "**Autodocumenting from %s" % os.path.abspath(os.curdir)
                modules = {}
                option_dict = self.distribution.get_option_dict('build_sphinx')
                source_dir = os.path.join(option_dict['source_dir'][1], 'api')
                if not os.path.exists(source_dir):
                    os.makedirs(source_dir)
                for pkg in self.distribution.packages:
                    if '.' not in pkg:
                        os.path.walk(pkg, _find_modules, modules)
                module_list = modules.keys()
                module_list.sort()
                autoindex_filename = os.path.join(source_dir, 'autoindex.rst')
                with open(autoindex_filename, 'w') as autoindex:
                    autoindex.write(""".. toctree::
   :maxdepth: 1

""")
                    for module in module_list:
                        output_filename = os.path.join(source_dir,
                                                       "%s.rst" % module)
                        heading = "The :mod:`%s` Module" % module
                        underline = "=" * len(heading)
                        values = dict(module=module, heading=heading,
                                      underline=underline)

                        print "Generating %s" % output_filename
                        _rst_template = ""
                        with open(output_filename, 'w') as output_file:
                            output_file.write(_rst_template % values)
                        autoindex.write("   %s.rst\n" % module)

            def run(self):
                if not os.getenv('SPHINX_DEBUG'):
                    self.generate_autoindex()

                for builder in self.builders:
                    self.builder = builder
                    self.finalize_options()
                    self.project = self.distribution.get_name()
                    self.version = self.distribution.get_version()
                    self.release = self.distribution.get_version()
                    BuildDoc.run(self)

        class LocalBuildLatex(LocalBuildDoc):
            builders = ['latex']

        cmdclass['build_sphinx'] = LocalBuildDoc
        cmdclass['build_sphinx_latex'] = LocalBuildLatex
    except ImportError:
        pass

    return cmdclass
