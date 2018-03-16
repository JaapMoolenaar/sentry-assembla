from __future__ import absolute_import

from social_auth.utils import setting
from sentry_plugins.client import AuthApiClient

class AssemblaClient(AuthApiClient):
    base_url = u'https://api.assembla.com/v1'
    users = {}

    def get_spaces(self):
        """Get all spaces available to this user"""
        return self.get('/spaces.json')

    def get_issue(self, space, issue_id):
        """Try and get a ticket bij ticket id"""
        if isinstance(issue_id, basestring) and len(issue_id) == 0:
            return None
        
        return self.get('/spaces/%s/tickets/id/%s' % (space, issue_id))

    def get_issue_by_number(self, space, issue_number):
        """Try and get a ticket bij ticket number"""
        if isinstance(issue_number, basestring) and len(issue_number) == 0:
            return None
        
        return self.get('/spaces/%s/tickets/%s' % (space, issue_number))

    def create_issue(self, space, data):
        """Create a ticket with the posted data, using the api"""
        assembla_data = {'summary': data['title'], 'description': data['description'], 'space_id': space}
        
        if data.get('parent_issue_id'):
            assembla_data['hierarchy_type'] = 1 #1 = Sub-task

        if data.get('assignee'):
            assembla_data['assigned_to_id'] = data['assignee']

        new_ticket = self.post('/spaces/%s/tickets' % space, data={'ticket': assembla_data})
        
        if data.get('parent_issue_id'):
            parent_issue = self.get_issue(space, data['parent_issue_id'])

            #1: Parent - Child
            #6: Story - Sub-Task
            relationship = 1
            if data.get('relationship'):
                relationship = data['relationship']
            
            self.post('/spaces/%s/tickets/%s/ticket_associations' % (space, parent_issue['number']), 
                data={'ticket1_id': parent_issue['id'],
                    'ticket2_id': new_ticket['id'],
                    'relationship': relationship}
            )
        
        return new_ticket

    def create_comment(self, space, issue, comment):
        """Create a comment on a ticket with the posted data"""
        return self.post(
            '/spaces/%s/tickets/%s/ticket_comments' % (space, issue['number']),
            data={'ticket_comment': {'comment': comment}},
        )

    def search_tickets(self, space, query, type='parent', page=1):
        """Search a ticket by the passed query
        Assembla sadly doesn't allow for searching, we thus have to 
        retrieve all pages to get a full result"""
        response = self.get(
            '/spaces/%s/tickets.json' % space,
            params={'page': page, 'per_page': 100, }
        )
        query = query.lower()

        filtered = [e for e in response if query in e['summary'].lower()]
        
        if setting('ASSEMBLA_TICKET_FILTER'):
            filtered = filter(setting('ASSEMBLA_TICKET_FILTER'), filtered)
        
        if type == 'parent' and setting('ASSEMBLA_PARENTTICKET_FILTER'):
            filtered = filter(setting('ASSEMBLA_PARENTTICKET_FILTER'), filtered)
        
        if len(response) >= 100:
            page += 1
            filtered += self.search_tickets(space, query, type, page)
        
        return filtered

    def search_users(self, space, query):
        """Get a list of all users in a space and filter it"""
        if (space not in self.users):
            self.users.update({
                space: self.get(
                    '/spaces/%s/users.json' % space,
                    params={}
                )
            })
            
        response = self.users[space]
        
        query = query.lower()

        filtered = [e for e in response if query in e['name'].lower() or query in e['login'].lower()]
        
        if setting('ASSEMBLA_USERS_FILTER'):
            filtered = filter(setting('ASSEMBLA_USERS_FILTER'), filtered)
            
        return filtered
