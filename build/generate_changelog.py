#!/usr/bin/env python

import argparse
import datetime
import getpass
import requests
import json

API_HOSTNAME = 'https://github.jpl.nasa.gov/api/v3/'

parser = argparse.ArgumentParser()
parser.add_argument('--user', help='Username to use for authentication')
parser.add_argument('--pass', help='Password to use for authentication')
parser.add_argument('--start-time', help='Start date range for tickets to find. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.')
parser.add_argument('--end-time', default=datetime.datetime.utcnow(), help='End date range for tickets to find. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.')
args = vars(parser.parse_args())

un = args['user']
if not un:
    un = raw_input('Username: ')

pw = args['pass']
if not pw:
    pw = getpass.getpass('Password: ')

url = API_HOSTNAME + 'repos/bliss/bliss-core/issues?state=all&per_page=100&sort=updated'
if args['start_time']:
    url += '&since={}'.format(args['start_time'])

r = requests.get(url, auth=(un, pw))
raw_issues = r.json()

while True:
    if 'next' not in r.links:
        break

    r = requests.get(r.links['next']['url'], auth=(un, pw))
    raw_issues += r.json()

issues = []
for issue in raw_issues:
    if 'pull_request' in issue:
        continue
    elif issue['closed_at'] == 'null' or issue['state'] != 'closed':
        continue
    elif args['end_time'] < datetime.datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ'):
        continue

    issues.append(issue)

for issue in issues:
    print 'Issue #{} - {}'.format(issue['number'], issue['title'])
