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


class Serializer(base.Serializer):
    format = 'python'


class Deserializer(base.Deserializer):

    format = 'python'

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        num_items = len(fixtures)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError
        fix_obj = fixtures[num_item]
        fixtures = fixtures[num_item + 1:]
        fixtures.append(fix_obj)
        return fixtures
