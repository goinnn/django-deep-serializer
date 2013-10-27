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

WALKING_STOP = 1
ONLY_REFERENCE = 2
WALKING_INTO_CLASS = 3


class BaseMetaWalkClass(object):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request=None, options=None):
        """
            Given the root object, the current object the request and some option,
            You can treatment the object before to serialize the object.
            This funcion is used at the serialization process.
        """
        return obj

    @classmethod
    def walking_into_class(cls, obj, field_name, model, request=None):
        """
            Given the the current object, the relation name and the model to the relation,
            You can determine if to walk into this model or not.
            This funcion is used at the serialization process.
        """
        return WALKING_INTO_CLASS

    @classmethod
    def get_queryset_to_relation(cls, obj, field_name, queryset, request=None):
        """
            Given the the current object, the relation name and the model to the relation,
            You can filter/exclude the result queryset
            This funcion is used at the serialization process.
        """
        return queryset

    @classmethod
    def pretreatment_fixture(cls, initial_obj, obj_fix, request=None):
        """
            Given a dictionary (fixtures dictionary) you can treatment it,
            before to deserialize the object.
            This funcion is used at the deserialization process.
        """
        return obj_fix

    @classmethod
    def pre_save(cls, initial_obj, obj, request=None):
        """
            Given a obj you can treatment this before the save a object.
            This funcion is used at the deserialization process.
        """
        pass

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        """
            Given a saved obj you can treatment this after the save a object.
            This is called after the every post_save signal
            This funcion is used at the deserialization process.
        """
        pass
