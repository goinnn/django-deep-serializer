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

from deep_serializer.settings import USE_INTERNAL_SERIALIZERS

if USE_INTERNAL_SERIALIZERS:
    from deep_serializer.serializers.base import DeserializationError
else:
    from django.core.serializers.base import DeserializationError

from deep_serializer import base
from deep_serializer.utils import findnth


class Serializer(base.Serializer):
    format = 'xml'


class Deserializer(base.Deserializer):

    format = 'xml'

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        token_object_start = '<object '
        token_object_end = '</object>'
        token_objects_end = '</django-objects>'
        num_items = fixtures.count(token_object_start)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError
        fixture_first_item_start = findnth(fixtures, token_object_start, 0)
        fixture_item_start = findnth(fixtures, token_object_start, num_item)
        fixture_item_end = findnth(fixtures, token_object_end, num_item)
        if fixture_item_start == -1 or fixture_item_end == -1:
            raise DeserializationError
        fixtures_item = fixtures[fixture_item_start:fixture_item_end + 9]
        fixtures = fixtures[:fixture_first_item_start] + fixtures[fixture_item_end + 9:]
        last_item_index = findnth(fixtures, token_objects_end, 0)
        if last_item_index == -1:
            raise DeserializationError
        fixtures = fixtures[:last_item_index] + fixtures_item + fixtures[last_item_index:]
        return fixtures
