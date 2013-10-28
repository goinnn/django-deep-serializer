# -*- coding: utf-8 -*-
# Copyright (c) 2013 by Pablo Martín <goinnn@gmail.com>
#
# This software is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import yaml

from deep_serializer import base
from deep_serializer import python_serializer


class Serializer(base.Serializer):
    format = 'yaml'


class Deserializer(python_serializer.Deserializer):

    format = 'yaml'

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        fixtures_python = yaml.load(fixtures, Loader=yaml.SafeLoader)
        fixtures_python = super(Deserializer, cls).deserialize_reorder(fixtures_python, num_item, num_reorder)
        fixtures = yaml.dump(fixtures_python)
        return fixtures

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures, walking_classes,
                              request=None, deserialize_options=None,
                              sorted_function=None):
        fixtures_python = yaml.load(fixtures)
        fixtures_python = super(Deserializer, cls).pretreatment_fixtures(
            initial_obj, fixtures_python, walking_classes,
            request=request, deserialize_options=deserialize_options,
            sorted_function=sorted_function)
        fixtures = yaml.dump(fixtures_python)
        return fixtures
