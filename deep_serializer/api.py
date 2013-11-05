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

# These status define the behaviour of the serializer, if the serializer
# have to continue serializing (WALKING_INTO_CLASS), only use the reference (ONLY_REFERENCE)
# or set this relation to none (WALKING_STOP).
# You can use these status in one2one, fk, m2m and reverse relations.
# For reverse relations only you can use WALKING_INTO_CLASS and ONLY_REFERENCE.


WALKING_STOP = 1
ONLY_REFERENCE = 2
WALKING_INTO_CLASS = 3


class BaseMetaWalkClass(object):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request=None, serialize_options=None):
        """
            Given the root object, the current object the request and some option,
            You can treatment the object before to serialize the object.
            This funcion is used at the serialization process.
        """
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        """
            Given the the current object, the relation name and the model to the relation,
            You can determine if to walk into this model or not.
            This funcion is used at the serialization process.
        """
        return WALKING_INTO_CLASS

    @classmethod
    def get_queryset_to_relation(cls, initial_obj, obj, field_name, queryset, request=None):
        """
            Given the the current object, the relation name and the model to the relation,
            You can filter/exclude the result queryset
            This funcion is used at the serialization process.
        """
        return queryset

    @classmethod
    def pretreatment_fixture(cls, initial_obj, obj_fix, request=None, deserialize_options=None):
        """
            Given a dictionary (fixtures dictionary) you can treatment it,
            before to deserialize the object.
            This funcion is used at the deserialization process.
            If you use xml format obj_fix will be a xml Element (instance of xml.dom.minidom.Element)
            This method only is called if you call to deserialize with pretreatment_fixtures = True,
            because this is costly
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
