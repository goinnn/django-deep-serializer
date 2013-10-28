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

from django import forms
from django.conf import settings

from example.app.models import WebSite

CHOICE_FIXTURES_FORMAT = (('json', 'JSON'),
                          ('xml', 'XML'),
                          ('yaml', 'YAML'),
                          ('python', 'Python'))


class WebSiteAdminForm(forms.ModelForm):

    class Meta:
        model = WebSite

    def __init__(self, *args, **kwargs):
        super(WebSiteAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['original_website'].queryset = self.fields['original_website'].queryset.exclude(pk=self.instance.pk)
            self.fields['initial_page'].queryset = self.fields['initial_page'].queryset.filter(website=self.instance)
        else:
            self.fields['initial_page'].queryset = self.fields['initial_page'].queryset.none()


class FormatFixturesForm(forms.Form):

    fixtures_format = forms.ChoiceField(choices=CHOICE_FIXTURES_FORMAT)

    def as_django_admin(self):
        if 'formadmin' in settings.INSTALLED_APPS:
            import formadmin
            return formadmin.forms.as_django_admin(self)
        return self
