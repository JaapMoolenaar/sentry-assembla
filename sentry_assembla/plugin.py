from __future__ import absolute_import

import six
import logging
import sentry_assembla
import os

from django.conf import settings

from rest_framework.response import Response

from sentry.exceptions import PluginError, PluginIdentityRequired
from sentry.plugins.bases.issue2 import IssueTrackingPlugin2, IssueGroupActionEndpoint
from sentry_plugins.base import CorePluginMixin

from sentry.utils.http import absolute_uri
from social_auth.utils import setting

from .client import AssemblaClient

env = os.environ.get

ERR_AUTH_NOT_CONFIGURED = (
    'You still need to associate an Assembla identity with this account.'
)

class AssemblaPlugin(CorePluginMixin, IssueTrackingPlugin2):
    description = 'Integrate Assembla issues by linking a repository to a project.'
    slug = 'assembla'
    title = 'Assembla'
    conf_title = title
    conf_key = 'assembla'
    auth_provider = 'assembla'
    author = 'Jaap Moolenaar'
    author_url = 'https://github.com/jaapmoolenaar'
    version = sentry_assembla.VERSION
    resource_links = [
        ('Bug Tracker', author_url + '/sentry-assembla/issues'),
        ('Source', author_url + '/sentry-assembla'),
    ]
    
# NEXT VERSION?
#    issue_fields = frozenset(['id', 'number', 'summary'])
    
    def get_group_urls(self):
        """Adds an extra url to allow for autocompletion in some selects"""
        return super(AssemblaPlugin, self).get_group_urls() + [
            (
                r'^autocomplete', IssueGroupActionEndpoint.as_view(
                    view_method_name='view_autocomplete',
                    plugin=self,
                )
            ),
        ]

    def is_configured(self, request, project, **kwargs):
        """Checks whether the option 'space' has been set in the configuration screen"""
        return bool(self.get_option('space', project))

    def has_space_access(self, space, choices):
        """Checks to see if space is one of the available choices"""
        for c, _ in choices:
            if space == c:
                return True
        return False

    def get_space_choices(self, spaces):
        """Return the spaces as tuples"""
        return [(w['id'], w['name']) for w in spaces]

    def get_relationship_choices(self):
        """These relationships are supported for now"""
        return [
            ('1', 'Parent - Child'),
            ('6', 'Story - Subtask'),
        ]

    def get_new_issue_fields(self, request, group, event, **kwargs):
        """Build the fields needed to create a ticket"""
        fields = super(AssemblaPlugin, self).get_new_issue_fields(request, group, event, **kwargs)
        
        client = self.get_client(request.user)
        
        spaces = client.get_spaces()
        space_choices = self.get_space_choices(spaces)
        space = self.get_option('space', group.project)
        if space and not self.has_space_access(space, space_choices):
            space_choices.append((space, space))

        default_parent_issue_number = self.get_option('parent_issue_number', group.project)
        default_parent_issue = client.get_issue_by_number(space, default_parent_issue_number)

        default_relationship = self.get_option('relationship', group.project)
                
        # use the same labels Assembla uses
        for field in fields:
            if field['name'] == 'title':
                field['label'] = 'Summary'
                field['required'] = True
            if field['name'] == 'description':
                field['label'] = 'Description'
                field['required'] = False

        return [
            {
                'name': 'space',
                'label': 'Assembla Space',
                'default': space,
                'type': 'select',
                'choices': space_choices,
                'readonly': True
            }
        ] + fields + [
            {
                'name': 'relationship',
                'label': 'Relationship',
                'default': default_relationship if default_relationship != None else 6,
                'type': 'select',
                'choices': self.get_relationship_choices(),
                'required': False,
                'placeholder': 'Select the type of relationship'
            }, {
                'name': 'parent_issue_id',
                'label': 'Parent ticket',
                'default': str(default_parent_issue['id']) if default_parent_issue != None else None,
                'type': 'select',
                'choices': [
                    (str(default_parent_issue['id']), '(#%s) %s' % (default_parent_issue['number'], default_parent_issue['summary'])),
                ] if default_parent_issue != None else None,
                'has_autocomplete': False if default_parent_issue != None else True,
                'required': False,
                'readonly': True if default_parent_issue != None else False,
                'placeholder': 'Start typing to search for a ticket in this space'
            }, {
                'name': 'assignee',
                'label': 'Assign to',
                'type': 'select',
                'has_autocomplete': True,
                'required': False,
                'placeholder': 'Start typing to search for a user'
            }
        ]

    def get_link_existing_issue_fields(self, request, group, event, **kwargs):
        """Build the fields needed to link a ticket"""
        return [
            {
                'name': 'issue_id',
                'label': 'Ticket',
                'default': '',
                'type': 'select',
                'has_autocomplete': True
            }, {
                'name': 'comment',
                'label': 'Comment',
                'default': absolute_uri(group.get_absolute_url()),
                'type': 'textarea',
                'help': ('Leave blank if you don\'t want to '
                         'add a comment to the Assembla issue.'),
                'required': False
            }
        ]

    def get_client(self, user):
        """Try and setup an API client"""
        auth = self.get_auth_for_user(user=user)
        if auth is None:
            raise PluginIdentityRequired(ERR_AUTH_NOT_CONFIGURED)
        
        return AssemblaClient(auth=auth)

    def error_message_from_json(self, data):
        """Convert an Assembla API error to a format Sentry can use"""
        error = data.get('error')
        if error:
            return error
        else:
            errors = data.get('errors')
            if errors:
                return ' '.join([e for e in errors['base']])
            
        return 'unknown error'

    def create_issue(self, request, group, form_data, **kwargs):
        """Handle a create issue form post"""
        client = self.get_client(request.user)

        try:
            response = client.create_issue(
                space=self.get_option('space', group.project), data=form_data
            )
        except Exception as e:
            self.raise_error(e, identity=client.auth)

        return response['id']
    
# NEXT VERSION?
#        return {
#            'id': response['id'],
#            'number': response['number'],
#            'summary': response['summary'],
#        }

    def link_issue(self, request, group, form_data, **kwargs):
        """Handle a link issue form post"""
        client = self.get_client(request.user)
        
        space = self.get_option('space', group.project)
        
        try:
            issue = client.get_issue(
                space=space,
                issue_id=form_data['issue_id'],
            )
        except Exception as e:
            self.raise_error(e, identity=client.auth)

        comment = form_data.get('comment')
        if comment:
            try:
                client.create_comment(space, issue, comment)
            except Exception as e:
                self.raise_error(e, identity=client.auth)
                
        #link_issue is expected to return an issue object containing a 'title'
        #https://github.com/getsentry/sentry/blob/8.22.0/src/sentry/plugins/bases/issue2.py#L278
        return {
            'title': issue['summary']
        }

# NEXT VERSION?
#        return {
#            'id': issue['id'],
#            'number': issue['number'],
#            'summary': issue['summary']
#        }

# NEXT VERSION?
#    def get_issue_label(self, group, issue, **kwargs):
#        if 'number' in issue:
#            return 'Assembla ticket (#%s)' % issue['number']
#        
#        return 'Assembla ticket'

    def get_issue_label(self, group, issue_id):
        """Generate a generic label"""
        return 'Assembla ticket'

# NEXT VERSION?
#    def get_issue_url(self, group, issue, **kwargs):
#        space = self.get_option('space', group.project)
#        
#        if 'number' in issue:
#            return 'https://app.assembla.com/spaces/%s/tickets/%s' % (space, issue['number'])
#
#        return 'https://app.assembla.com/spaces/%s/tickets' % space

    def get_issue_url(self, group, issue_id):
        """Generate a generic url, v8.22 doesn't allow 
        storing more values for an issue"""
        space = self.get_option('space', group.project)
        
        # This is a full url actualy, we're missing the url
        return 'https://app.assembla.com/spaces/%s/tickets' % space

    def validate_config(self, project, config, actor):
        """Validate available config"""
        try:
            config['space'] = config['space']
        except ValueError as exc:
            self.logger.exception(six.text_type(exc))
            raise PluginError('Invalid space value')
        return config

    def get_config(self, *args, **kwargs):
        """Generate the fields to configure this plugin"""
        user = kwargs['user']
        try:
            client = self.get_client(user)
        except PluginIdentityRequired as e:
            self.raise_error(e)
            
        spaces = client.get_spaces()
        space_choices = self.get_space_choices(spaces)
        space = self.get_option('space', kwargs['project'])
        
        # check to make sure the current user has access to the space
        helptext = None
        if space and not self.has_space_access(space, space_choices):
            space_choices.append((space, space))
            helptext = (
                'This plugin has been configured for an Assembla space '
                'that either you don\'t have access to or doesn\'t '
                'exist. You can edit the configuration, but you will not '
                'be able to change it back to the current configuration '
                'unless a teammate grants you access to the space in Assembla.'
            )
        return [
            {
                'name': 'space',
                'label': 'Space',
                'type': 'select',
                'choices': space_choices,
                'default': space or spaces[0]['id'],
                'help': helptext
            }, {
                'name': 'parent_issue_number',
                'label': 'Parent ticket (enter a ticket number)',
                'type': 'number',
                'required': False,
                'placeholder': '(Optional) Enter a parent ticket number which will be selected by default'
            }, {
                'name': 'relationship',
                'label': 'Default relationship',
                'type': 'select',
                'choices': self.get_relationship_choices(),
                'required': False,
                'placeholder': '(Optional) Set the default relationship between the new ticket and parent'
            }
        ]

    def view_autocomplete(self, request, group, **kwargs):
        """A 'route' to generate select options in the forms"""
        field = request.GET.get('autocomplete_field')
        query = request.GET.get('autocomplete_query')

        client = self.get_client(request.user)
        space = self.get_option('space', group.project)
        
        results = []
        field_name = field
        if field == 'issue_id' or field == 'parent_issue_id':
            response = client.search_tickets(
                space, 
                query.encode('utf-8'),
                'parent' if field == 'parent_issue_id' else 'regular'
            )
            results = [
                {
                    'text': '(#%s) %s' % (i['number'], i['summary']),
                    'id': i['id']
                } for i in response
            ]
        elif field == 'assignee':
            response = client.search_users(space, query.encode('utf-8'))
            results = [
                {
                    'text': '%s (%s)' % (i['name'], i['login']),
                    'id': i['id']
                } for i in response
            ]
        return Response({field: results})
    
    def setup(self, bindings):
        settings.AUTH_PROVIDERS.update({
            'assembla': ('ASSEMBLA_CLIENT_ID', 'ASSEMBLA_CLIENT_SECRET'),
        })
        
        settings.AUTH_PROVIDER_LABELS.update({
            'assembla': 'Assembla',
        })
        
        settings.AUTHENTICATION_BACKENDS += (
            'sentry_assembla.social_auth.AssemblaBackend',
        )
        
        settings.SOCIAL_AUTH_AUTHENTICATION_BACKENDS += (
            'sentry_assembla.social_auth.AssemblaBackend',
        )
        
        if setting('ASSEMBLA_CLIENT_ID') == None:
            settings.ASSEMBLA_CLIENT_ID = env('ASSEMBLA_CLIENT_ID') or None
        
        if setting('ASSEMBLA_CLIENT_SECRET') == None:
            settings.ASSEMBLA_CLIENT_SECRET = env('ASSEMBLA_CLIENT_SECRET') or None
            
        if setting('ASSEMBLA_CLIENT_ID') == None or setting('ASSEMBLA_CLIENT_SECRET') == None:
            self.logger.info('Assembla client id or secret not set')