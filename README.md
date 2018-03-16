Sentry-Assembla
===============
_I created this plugin with not much knowledge of Python, please keep that in 
mind._

This plugin is developed using the Senty on premise *v8.22* docker image

In this version, a link to the Assembla ticket is harder to create.
This is because assembla requires a ticket number in the url, whilst sentry
stores it's ID. Getting the ticket number afterwards is hard, because an API
client can't be contructed.

A new version for Sentry is however on the horizon, this version allows storage 
of more data per issue, thus allowing me to store the ticket number and 
generating a valid link.


Installation
============

This package is not on PyPI yet, please install using:

`sudo -H pip install -e git+https://github.com/jaapmoolenaar/sentry-assembla#egg=sentry_assembla`

Or add the following to your requirements.txt in the docker on premise path:

`-e git+https://github.com/jaapmoolenaar/sentry-assembla#egg=sentry_assembla`


Configuration
=============

The Assembla API requires a client ID and Key.
These can be created here: https://app.assembla.com/user/edit/manage_clients
A valid redirect url would be: 

`<hostname>/account/settings/social/associate/complete/assembla/`

This can be set in the sentry.conf.py file:

```python
ASSEMBLA_CLIENT_ID = 'id'
ASSEMBLA_CLIENT_SECRET = 'secret'
```

Or using environment variables with the same name in for instance docker-compose.yml:

```yml
version: '2'
services:
  base:
    environment:
      ASSEMBLA_CLIENT_ID: 'id'
      ASSEMBLA_CLIENT_SECRET: 'secret'
```

A few lambda functions can be configured:

- Filter tickets while searching (example):

`ASSEMBLA_TICKET_FILTER = lambda ticket: ticket['summary'].lower().startswith('project:')`

- Filter *parent* tickets while searching (example):

`ASSEMBLA_PARENTTICKET_FILTER = lambda ticket: ticket['number'] == '1'`

- Filter users while searching (example):

`ASSEMBLA_USERS_FILTER = lambda user: user['organization'] != None`