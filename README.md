# sameuser.py
See the companion blog post [Exploring Users With Multiple Accounts In BloodHound](https://insomniasec.com/blog/bloodhound-shared-accounts).

```
usage: sameuser.py [-h] [--same-csv SAME_CSV]
                   [--same-regex-find SAME_REGEX_FIND]
                   [--same-regex-replace SAME_REGEX_REPLACE] [--same-username]
                   [--same-email] [--same-displayname] [--password PASSWORD]
                   [--clear] [--clear-user] [--clear-password]

optional arguments:
  -h, --help            show this help message and exit
  --same-csv SAME_CSV   Use a CSV file containing mapped users to add SameUser
                        relationships
  --same-regex-find SAME_REGEX_FIND
                        Use a Python regular expression to map users and add
                        SameUser relationships, example: "(.*)(@.*)"
  --same-regex-replace SAME_REGEX_REPLACE
                        Python regular expression to manipulate the username
                        found by --same-regex-find, example: "\1-ADMIN\2"
  --same-username       Find users with the same username (in different
                        domains) and add SameUser relationships
  --same-email          Find users with the same email address and add
                        SameUser relationships
  --same-displayname    Find users with the same display name and add SameUser
                        relationships
  --password PASSWORD   Find users with SameUser relationships who have set
                        their password within X hours and add SharedPassword
                        relationships
  --clear               Remove all SameUser and SharedPassword relationships
                        in the database
  --clear-user          Remove all SameUser relationships in the database
  --clear-password      Remove all SharedPassword relationships in the
                        database
```
