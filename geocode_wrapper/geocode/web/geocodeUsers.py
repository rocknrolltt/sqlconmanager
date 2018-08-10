#!/usr/bin/env python

import os
import logging
import base64

from flask import current_app
from flask_login import UserMixin

logger = logging.getLogger(__name__)

'''
Class representation of a user contained in our db file.
Simple representation includes user id and api key
'''


class GeocodeUser(UserMixin):
    def __init__(self, userid, key):
        self.id = userid
        self.api_key = key

    # method takes a key and db connection (file name)
    # attempts to get user from db, returns None if no user found
    # key can be api key or user name (key item is set to 1 (api) as default)
    @classmethod
    def get_user(cls, key, db_conn, keyitem=1):
        logger.info("Opening %s", db_conn)
        logger.debug("Key item: %d", keyitem)

        try:
            with open(db_conn, 'r') as db:
                for line in db:
                    line = line.strip()
                    items = line.split(' ', 1)
                    if key == items[keyitem]:
                        break
                else:
                    logger.info("No match")
                    return None

                logger.info("User %s is found", items[0])
                return cls(*items)
        except IOError:
            logger.error("Database file could not be found")
            return None


'''
This is our request handler method for authentication. Method will try to
authenticate using the api key first, and Basic Authorization as a second
option. If it can't authenticate, we return None and flask will throw a 401
exception. Method that need authentication should use the login_required decorator
in order for this method to be called
'''


def request_user(request):
    logger.debug("request_user()... getting api_key from request args")
    api_key = request.args.get('key')

    user_db = current_app.config['userdb']
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    user_db = os.path.join(cur_dir, user_db)

    # if api key exists and user can be found with that key
    # authentication is successful and we return the user
    if api_key:
        user = GeocodeUser.get_user(api_key, user_db)
        if user:
            return user

    logger.debug("request_user()... now trying from request headers")

    api_key = request.headers.get('Authorization')

    if api_key:
        api_key = api_key.replace('Basic ', '', 1)
        try:
            api_key = base64.b64decode(api_key)
        except TypeError:
            pass

        user = GeocodeUser.get_user(api_key, user_db)
        if user:
            return user

    return None