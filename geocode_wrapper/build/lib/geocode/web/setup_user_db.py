#!/usr/bin/env python
from __future__ import print_function
import os.path

if __name__ == '__main__':
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Add/Remove users from a Geocoder"
                                        " userdb.")
    parser.add_argument("userdb", help="userdb filename")
    parser.add_argument("action", choices=['add', 'remove'],
                        help="Action to take: %(choices)s")
    parser.add_argument("user", help="username")

    args = parser.parse_args()

    #load_user_db(args.userdb)
    if os.path.exists(args.userdb):
        lines = [ln.strip().split(' ', 1) for ln in open(args.userdb, 'r')]
    else:
        lines = []

    if args.action == 'add':
        import uuid
        # Generate a unique id to use as an api key
        api_key = str(uuid.uuid4())

        try:
            for user, _ in lines:
                if user == args.user:
                    raise Exception("User %s is already in the database" %
                                    args.user)
            else:
                lines.append((args.user, api_key))
        except Exception as ex:
            print("Failed to add user %s: %s" % (args.user, ex))
            sys.exit(-1)
        else:
            print("User %s has api_key: %s" % (args.user, api_key))

    if args.action == 'remove':
        try:
            for i, (user, _) in enumerate(lines):
                if user == args.user:
                    break
            else:
                raise Exception("User %s is not in the database" %
                                args.user)
            lines.pop(i)
        except Exception as ex:
            print("Failure while removing user %s: %s" % (args.user, ex))
            sys.exit(-1)
        else:
            print("Successfully removed user %s" % args.user)

    with open(args.userdb, 'w') as fh:
        for user, apikey in lines:
            fh.write("%s %s\n" % (user, apikey))
    print("%s has been updated" % args.userdb)


