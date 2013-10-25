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
from functools import update_wrapper

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404


from example.app.forms import WebSiteAdminForm
from example.app.models import WebSite, Page
from example.app.utils import clone_website


class WebSiteAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'slug')
    form = WebSiteAdminForm

    def get_urls(self):
        urlpatterns = super(WebSiteAdmin, self).get_urls()
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = patterns('',
            url(r'^(.+)/clone/$',
                wrap(self.clone_website),
                name='clone_website'),
        ) + urlpatterns
        return urlpatterns

    def clone_website(self, request, object_id, form_url='', extra_context=None):
        website = get_object_or_404(WebSite, pk=object_id)
        objs = clone_website(website)
        return HttpResponseRedirect(reverse('admin:app_website_change', args=(objs[0].pk,)))


class PageAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'slug', 'website')


admin.site.register(WebSite, WebSiteAdmin)
admin.site.register(Page, PageAdmin)
