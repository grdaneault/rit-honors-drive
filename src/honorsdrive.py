"""
This Is the base of the RIT Honors Drive Program.
"""


#!/usr/bin/python2

import jinja2
import os
import sys

import fix_path 
from pages import About
from pages import User
from pages import TransferOwnership



# import drivebase
# from apiclient import errors
# from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

# from oauth2client.client import AccessTokenRefreshError

JINJA_ENVIRONMENT = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
        extensions=['jinja2.ext.autoescape'])



# Create an WSGI application suitable for running on App Engine
app = webapp.WSGIApplication(
        [('/', TransferOwnership.TransferOwnershipHandler),
         ('/about', About.AboutHandler),
         ('/user',  User.UserHandler)],
        # TODO: Set to False in production.
        debug=True
)


def main():
    """Main entry point for executing a request with this handler."""
    run_wsgi_app(app)


if __name__ == "__main__":
    main()
