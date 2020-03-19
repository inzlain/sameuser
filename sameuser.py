from neo4j import GraphDatabase
from itertools import combinations
import argparse
import re
import csv

uri = 'bolt://127.0.0.1:7687'
username = 'neo4j'
password = 'changeme'
driver = GraphDatabase.driver(uri, auth=(username, password), encrypted=False)

parser = argparse.ArgumentParser()
parser.add_argument('--same-csv', help='Use a CSV file containing mapped users to add SameUser relationships')
parser.add_argument('--same-regex-find', help=r'Use a Python regular expression to map users and add SameUser relationships, example: "(.*)(@.*)"')
parser.add_argument('--same-regex-replace', help=r'Python regular expression to manipulate the username found by --same-regex-find, example: "\1-ADMIN\2"')
parser.add_argument('--same-username', help='Find users with the same username (in different domains) and add SameUser relationships', action='store_true')
parser.add_argument('--same-email', help='Find users with the same email address and add SameUser relationships', action='store_true')
parser.add_argument('--same-displayname', help='Find users with the same display name and add SameUser relationships', action='store_true')
parser.add_argument('--password', help='Find users with SameUser relationships who have set their password within X hours and add SharedPassword relationships', type=int)
parser.add_argument('--clear', help='Remove all SameUser and SharedPassword relationships in the database', action='store_true')
parser.add_argument('--clear-user', help='Remove all SameUser relationships in the database', action='store_true')
parser.add_argument('--clear-password', help='Remove all SharedPassword relationships in the database', action='store_true')
args = parser.parse_args()


def all_usernames():
    session = driver.session()
    users = []
    result = session.run('MATCH (u:User) RETURN u.name')
    for record in result.records():
        username = record.get('u.name')
        if username != None:
            users.append(username)
    session.close
    return users


def same_add(user_a, user_b):
    # Check to prevent adding any self relationships
    if user_a != user_b:
        print('{0} -> {1}... '.format(user_a, user_b), end = '')
        session = driver.session()
        # Check that both users exist
        query = 'MATCH (u:User {{name:"{0}"}}) RETURN u.name'
        user_a_result = session.run(query.format(user_a))
        user_b_result = session.run(query.format(user_b))
        if user_a_result.single() == None:
            print(' user {0} not found'.format(user_a))
        elif user_b_result.single() == None:
            print(' user {0} not found'.format(user_b))
        else:
            # Add a SameUser relationship between the users
            query = 'MATCH (a:User {{name:"{0}"}}), (b:User {{name:"{1}"}}) MERGE (a)-[r1:SameUser]->(b)-[r2:SameUser]->(a) RETURN a.name, b.name'.format(user_a, user_b)
            result = session.run(query)
            new_relationships = result.summary().counters.relationships_created
            if new_relationships != 0:
                print(' added SameUser relationship')
            else:
                print(' relationship already exists')

        session.close

def same_csv():
    with open(args.same_csv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            user_a = row[0].upper().replace(' ', '')
            user_b = row[1].upper().replace(' ', '')
            same_add(user_a, user_b)

def same_regex():
    for user_a in all_usernames():
        user_b = re.sub(args.same_regex_find, args.same_regex_replace, user_a)
        same_add(user_a, user_b)


def same_username():
    session = driver.session()
    for user_a in all_usernames(): # somewhat inefficient as we end up checking all relationships form both directions
        username_match = re.match(r'(.*@).*', user_a) # ignoring usernames without a domain
        if (username_match != None):
            if len(username_match.groups()) > 0:
                username = username_match.group(1)
                # Blacklist of common built-in accounts
                if username != "KRBTGT@" and username != "ADMINISTRATOR@" and username != "GUEST@":
                    query = 'MATCH (b:User) WHERE (b.name STARTS WITH "{0}" AND NOT b.name = "{1}") RETURN b.name'.format(username, user_a)
                    result = session.run(query)
                    for record in result.records():
                        same_add(user_a, record.get('b.name'))
    session.close

def same_displayname():
    session = driver.session()
    displaynames = []
    result = session.run('MATCH (u:User) RETURN u.displayname, COUNT(u.displayname)')
    for record in result.records():
        if record.get('COUNT(u.displayname)') > 1:
            displaynames.append(record.get('u.displayname'))
    for displayname in displaynames:
        if displayname != None and displayname != '':
            users = []
            query = 'MATCH (u:User) WHERE u.displayname = "{0}" RETURN u.name'.format(displayname)
            result = session.run(query)
            for record in result.records():
                users.append(record.get('u.name'))
            for user_combination in list(combinations(users, 2)):
                same_add(user_combination[0], user_combination[1])
    session.close

def same_email():
    session = driver.session()
    emails = []
    result = session.run('MATCH (u:User) RETURN u.email, COUNT(u.email)')
    for record in result.records():
        if record.get('COUNT(u.email)') > 1:
            emails.append(record.get('u.email'))
    for email in emails:
        if email != None and email != '':
            users = []
            query = 'MATCH (u:User) WHERE u.email = "{0}" RETURN u.name'.format(email)
            result = session.run(query)
            for record in result.records():
                users.append(record.get('u.name'))
            for user_combination in list(combinations(users, 2)):
                same_add(user_combination[0], user_combination[1])
    session.close

def shared_password():
    time_window = 60 * 60 * int(args.password) # BloodHound stores pwdlastset in Unix epoch format
    session = driver.session()
    query = 'MATCH (a:User), (b:User), p=(a)-[r:SameUser]-(b) WHERE a.pwdlastset < b.pwdlastset+{0} AND a.pwdlastset > b.pwdlastset-{0} AND a.pwdlastset > 0 AND b.pwdlastset > 0 MERGE (a)-[r1:SharedPassword]->(b)-[r2:SharedPassword]->(a) RETURN a.name, b.name'
    result = session.run(query.format(time_window))
    new_relationships = result.summary().counters.relationships_created
    if new_relationships != 0:
        print('Added SharedPassword relationships between {0} user pairs'.format(int(new_relationships / 2)))
    else:
        print('No new SharedPassword relationships added')
    session.close


def clear_sameuser():
    print('Clearing all SameUser relationships... ', end = '')
    session = driver.session()
    result = session.run('MATCH (a:User)-[r:SameUser]->(b:User) DELETE r')
    session.close()
    print('OK')

def clear_sharedpassword():
    print('Clearing all SharedPassword relationships... ', end = '')
    session = driver.session()
    result = session.run('MATCH (a:User)-[r:SharedPassword]->(b:User) DELETE r')
    session.close()
    print('OK')


if args.clear:
    clear_sameuser()
    clear_sharedpassword()

if args.clear_user:
    clear_sameuser()

if args.clear_password:
    clear_sharedpassword()

if args.same_csv:
    same_csv()

if args.same_regex_find and args.same_regex_replace:
    same_regex()

if args.same_username:
    same_username()

if args.same_displayname:
    same_displayname()

if args.same_email:
    same_email()

if args.password:
    shared_password() 


driver.close()
