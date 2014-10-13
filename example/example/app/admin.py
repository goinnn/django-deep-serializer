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
from django.contrib import messages
from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext

from example.app.forms import WebSiteAdminForm, FormatFixturesForm
from example.app.models import WebSite, Page
from example.app.utils import clone_website, serialize_website


class WebSiteAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'slug')
    filter_horizontal = ('owners',)
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
            url(r'^(.+)/clone/with-owners/$',
                wrap(self.clone_website_with_users),
                name='clone_website'),
            url(r'^(.+)/serialize/$',
                wrap(self.serialize_website),
                name='clone_website'),
            url(r'^(.+)/serialize/natural-keys/$',
                wrap(self.serialize_website_natural_keys),
                name='clone_website'),
        ) + urlpatterns
        return urlpatterns

    def serialize_website(self, request, object_id, form_url='', extra_context=None, action='restore'):
        website = self.get_object(request, unquote(object_id))
        data = request.GET or None
        form = FormatFixturesForm(data=data)
        if form.is_valid():
            fixtures_format = form.cleaned_data['fixtures_format']
            fixtures_extension = fixtures_format
            if fixtures_extension == 'python':
                fixtures_extension = 'py'
            serialize_options = {'only_serializer': True}
            fixtures = serialize_website(website, action=action, format=fixtures_format, serialize_options=serialize_options)
            if fixtures_format == 'python':
                fixtures = str(fixtures)
            response = HttpResponse(fixtures, content_type='application/%s' % fixtures_format)
            response['Content-Disposition'] = 'attachment; filename=website_%s.%s' % (website.pk, fixtures_extension)
            return response
        opts = self.model._meta
        return render_to_response('admin/app/website/serialize_form.html',
                                  {'original': website,
                                   'app_label': opts.app_label,
                                   'opts': opts,
                                   'form': form,
                                   'title': ugettext('Serialize WebSite')},
                                  context_instance=RequestContext(request))

    def serialize_website_natural_keys(self, request, object_id, form_url='', extra_context=None):
        return self.serialize_website(request, object_id,
                                      form_url=form_url,
                                      extra_context=extra_context,
                                      action='restore-natural-keys')

    def clone_website(self, request, object_id, form_url='', extra_context=None, action='clone'):
        website = self.get_object(request, unquote(object_id))
        if request.method == 'POST':
            objs = clone_website(website, action=action)
            messages.info(request, ugettext('Created %s objects succesfully') % len(objs))
            return HttpResponseRedirect(reverse('admin:app_website_change', args=(objs[0].pk,)))
        opts = self.model._meta
        return render_to_response('admin/app/website/clone_form.html',
                                  {'original': website,
                                   'app_label': opts.app_label,
                                   'opts': opts,
                                   'title': ugettext('Clone WebSite')},
                                  context_instance=RequestContext(request))

    def clone_website_with_users(self, request, object_id, form_url='', extra_context=None):
        return self.clone_website(request, object_id,
                                  form_url=form_url,
                                  extra_context=extra_context,
                                  action='clone-with-owners')


class PageAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'slug', 'website')


admin.site.register(WebSite, WebSiteAdmin)
admin.site.register(Page, PageAdmin)
