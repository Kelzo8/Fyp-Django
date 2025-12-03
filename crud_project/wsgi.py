"""
WSGI config for crud_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crud_project.settings')

# Initialize New Relic agent
import newrelic.agent
newrelic.agent.initialize(os.path.join(os.path.dirname(__file__), 'newrelic.ini'))

application = get_wsgi_application()
