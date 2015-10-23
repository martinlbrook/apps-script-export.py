#!/usr/bin/env python3

#    Copyright 2015 Martin Brook
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import httplib2
import os
import sys
import argparse
import json
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

SCOPES = (
    'https://www.googleapis.com/auth/drive', 
    'https://www.googleapis.com/auth/drive.scripts'
)
DEFAULT_CREDENTIALS_FILENAME = 'credentials.json'
CLIENT_SECRET_FILENAME = 'client_secret.json'

APPLICATION_NAME = 'Apps Script Export Tool'
DATA_DIR = os.path.join(os.path.expanduser('~'), '.apps-script-export')


def get_credentials(credential_file, flags):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """

    store = oauth2client.file.Storage(credential_file)
    credentials = store.get()
    if not credentials or credentials.invalid:
        clientsecret = os.path.join(DATA_DIR, CLIENT_SECRET_FILENAME)
        flow = client.flow_from_clientsecrets(clientsecret, SCOPES)

        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_file)
    return credentials

def client_secrets_help():
    print("In order to use this script, you need to provide your own "
        "client_secret.json file, which can be obtained from the "
        "Google Developer Console.\n\n"
        "For further details see here: "
        "https://developers.google.com/drive/web/quickstart/python")


def main():
    """Exports an Apps Script project from Google Drive."""

    # Ensure data folder exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Parse command line flags
    argparser = argparse.ArgumentParser(parents=[tools.argparser])

    argparser.add_argument(
        '--credential_file',
        default = os.path.join(DATA_DIR, DEFAULT_CREDENTIALS_FILENAME),
        help = 'A file which will be used to read or store oauth2 credentials'
    )
    
    argparser.add_argument(
        'script_id',
        help = "The ID of the Apps Script to download"
    )

    flags = argparser.parse_args()
    
    # Obtain an authorized Http object
    try:
        credentials = get_credentials(flags.credential_file, flags)
    except oauth2client.clientsecrets.InvalidClientSecretsError as e:
        print("Error reading client secrets: " + str(e))
        client_secrets_help()
        sys.exit()

    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)

    # Get the project file requested and obtain the JSON export link
    f = service.files().get(fileId=flags.script_id).execute()
    exportLink = f['exportLinks']['application/vnd.google-apps.script+json']

    print("Exporting Apps Script project '{}'...\n".format(f['title']))
    
    # Request and parse the JSON file containing the script data
    resp, content = http.request(exportLink, "GET")
    data = json.loads(content.decode('utf-8'))
    
    # Output the script and HTML files for the project
    for f in data['files']:
        if f['type'] == 'server_js': ext = '.js'
        elif f['type'] == 'html': ext = '.html'
        else: ext = ''
        
        filename = f['name'] + ext
        with open(filename, mode = 'w') as of:
            of.write(f['source'])
            print("{} written".format(filename))
    
    print("\nSync complete, {} files updated.".format(len(data['files'])))

if __name__ == '__main__':
    main()
