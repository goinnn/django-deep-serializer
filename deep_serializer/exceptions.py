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


class DoesNotNaturalKeyException(Exception):
    pass


class DeepSerializerDoesNotExist(Exception):
    pass


def update_the_serializer(obj, field_name):
    msg = 'Please update the serializer this class: %s has not define the behavior to this relation: %s' % (obj.__class__.__name__, field_name)
    raise DeepSerializerDoesNotExist(msg)
