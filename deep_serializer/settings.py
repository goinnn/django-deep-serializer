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

from django.conf import settings

serialization_modules = getattr(settings, 'SERIALIZATION_MODULES', False)

if serialization_modules and isinstance(serialization_modules, dict):
    for serializer in serialization_modules.values():
        if serializer.startswith('deep_serializer.'):
            USE_INTERNAL_SERIALIZERS = True
        else:
            USE_INTERNAL_SERIALIZERS = False
else:
    USE_INTERNAL_SERIALIZERS = False
