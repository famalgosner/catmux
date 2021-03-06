# -- BEGIN LICENSE BLOCK ----------------------------------------------

# catmux
# Copyright (C) 2018  Felix Mauch
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# -- END LICENSE BLOCK ------------------------------------------------

"""Contains everything around the config file"""
from __future__ import print_function

import re
import yaml

from window import Window
import tmux_wrapper as tmux


class Session(object):

    """Parser for a config yaml file"""

    def __init__(self, runtime_params=None):
        """TODO: to be defined1. """

        self._common = dict()
        self._parameters = dict()
        self._runtime_params = self._parse_overwrites(runtime_params)
        self._windows = list()
        self.__yaml_data = None

    def init_from_filepath(self, filepath):
        """Initializes the data from a file read from filepath."""

        try:
            self.__yaml_data = yaml.load(file(filepath, 'r'))
        except yaml.YAMLError as exc:
            print('Error while loading config file: %s', exc)
            print('Loaded file was: %s', filepath)

        self.init_from_yaml(self.__yaml_data)

    def init_from_yaml(self, yaml_data):
        """Initialize config directly by an already loaded yaml structure."""

        self.__yaml_data = yaml_data
        self._parse_common()
        self._parse_parameters()
        self._parse_windows()

    def run(self, debug=False):
        """Runs the loaded session"""
        if len(self._windows) == 0:
            print('No windows to run found')
            return

        first = True
        for window in self._windows:
            window.create(first)
            if debug:
                window.debug()
            first = False

        if 'default_window' in self._common:
            tmux.tmux_call(['select-window', '-t', self._common['default_window']])


    def _parse_common(self):
        if self.__yaml_data is None:
            print('parse_common was called without yaml data loaded.')
            raise RuntimeError

        if 'common' in self.__yaml_data:
            self._common = self.__yaml_data['common']

    def _parse_overwrites(self, data_string):
        """Separates a comma-separated list of foo=val1,bar=val2 into a dictionary."""
        if data_string is None:
            return None

        overwrites = dict()
        param_list = data_string.split(',')
        for param in param_list:
            key, value = param.split('=')
            overwrites[key] = value

        return overwrites

    def _parse_parameters(self):
        if self.__yaml_data is None:
            print('parse_parameters was called without yaml data loaded.')
            raise RuntimeError
        if 'parameters' in self.__yaml_data:
            self._parameters = self.__yaml_data['parameters']

        print('Parameters found in session config:')
        print(' - ' + '\n - '.join('{} = {}'.format(key, value)
                                   for key, value in self._parameters.items()))
        if self._runtime_params:
            print('Parameters found during runtime (overwrites):')
            print(' - ' + '\n - '.join('{} = {}'.format(key, value)
                                       for key, value in self._runtime_params.items()))
            # Overwrite parameters given from command line
            self._parameters.update(self._runtime_params)


        self._replace_parameters(self.__yaml_data)

    def _replace_parameters(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = self._replace_parameters(value)
        elif isinstance(data, list):
            for index, item in enumerate(data):
                data[index] = self._replace_parameters(item)
        elif isinstance(data, str):
            for key, value in self._parameters.items():
                # print('-\nValue {}: {}\n='.format(value, type(data)))
                # if isinstance(value, str):
                # print('replacing {} in {}'.format(key, data))
                data = re.sub(r"\${%s}"%(key), str(value), data)
        return data


    def _parse_windows(self):
        if self.__yaml_data is None:
            print('parse_windows was called without yaml data loaded.')
            raise RuntimeError

        if 'windows' in self.__yaml_data:
            for window in self.__yaml_data['windows']:
                if 'if' in window:
                    print('Detected of condition for window ' + window['name'])
                    if window['if'] not in self._parameters:
                        print('Skipping window ' + window['name'] + ' because parameter ' +
                              window['if'] + ' was not found.')
                        continue
                    elif not self._parameters[window['if']]:
                        print('Skipping window ' + window['name'] + ' because parameter ' +
                              window['if'] + ' is switched off globally')
                        continue
                    else:
                        print('condition fulfilled: {} == {}'
                              .format(window['if'], self._parameters[window['if']]))
                if 'unless' in window:
                    print('Detected unless condition for window ' + window['name'])
                    if self._parameters[window['unless']]:
                        print('Skipping window ' + window['name'] + ' because parameter ' +
                              window['unless'] + ' is switched on globally')
                        continue
                    else:
                        print('condition fulfilled: {} == {}'
                              .format(window['unless'], self._parameters[window['unless']]))

                kwargs = dict()
                if 'before_commands' in self._common:
                    kwargs['before_commands'] = self._common['before_commands']

                kwargs.update(window)

                self._windows.append(Window(**kwargs))
        else:
            print('No window section found in session config')
