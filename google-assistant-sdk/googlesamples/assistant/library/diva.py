#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import logging
import os
import os.path
import pathlib2 as pathlib
import platform
import sys
import subprocess
import threading
 
import google.oauth2.credentials

from firebase import firebase
from google.assistant.library import Assistant
from google.assistant.library.event import EventType
from google.assistant.library.file_helpers import existing_file
from google.assistant.library.device_helpers import register_device

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

DEVICE_API_URL = 'https://embeddedassistant.googleapis.com/v1alpha2'

COMMANDS = {}
COMMANDS['0004368999'] = "Riproduci Peppa Pig da Netflix"

class MyAssistant(object):

    def __init__(self, credentials_file, project_id, device_model_id):
        self._assistant = None
        self._device_model_id = device_model_id
        self._project_id = project_id
        self._can_configure = False
        self._can_start_conversation = False
        self._credentials_file = credentials_file
        self._task = threading.Thread(target=self._run_task)

    def start(self):
        """Starts the assistant.
        Starts the assistant event loop and begin processing events.
        """
        self._task.daemon = True
        self._task.start()

    def _run_task(self):
        with open(self._credentials_file, 'r') as f:
            self._credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))

        with Assistant(self._credentials,self._device_model_id) as assistant:
            self._assistant = assistant
            self._device_id = 'assistantsdk-170114-project-diva-jy6ql4'
            print('device_model_id:', self._device_model_id + '\n' +
                  'device_id:', self._assistant.device_id + '\n')
            if self._project_id!='':
                self._register_device()
            for event in assistant.start():
                self._process_event(event)

    def _process_event(self, event):
        print(event)
        if event.type == EventType.ON_START_FINISHED:
            self._can_start_conversation = True
            # Start the Assistant SDK
            if sys.stdout.isatty():
                print('Say "OK, Google" or press the button, then speak. '
                      'Press Ctrl+C to quit...')
        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            self._can_start_conversation = False

        elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
              or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
              or event.type == EventType.ON_NO_RESPONSE):
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _register_device(self):
        base_url = '/'.join([DEVICE_API_URL, 'projects', self._project_id, 'devices'])
        device_url = '/'.join([base_url, self._device_id])
        session = google.auth.transport.requests.AuthorizedSession(self._credentials)
        r = session.get(device_url)
        print(device_url, r.status_code)
        if r.status_code == 404:
            print('Registering....')
            r = session.post(base_url, data=json.dumps({
                'id': self._device_id,
                'model_id': self._device_model_id,
                'client_type': 'SDK_LIBRARY'
            }))
            if r.status_code != 200:
                raise Exception('failed to register device: ' + r.text)
            print('\rDevice registered.')

    def _repeat_after_me(self, message):
        self._assistant.set_mic_mute(True)
        self._assistant.start_conversation()
        self._assistant.send_text_query('Ripeti dopo di me %s' % message)
        self._assistant.set_mic_mute(False)

    def send_text(self, message):
        if self._can_start_conversation:
            print('Sending text message: %s' % message)
            self._assistant.set_mic_mute(True)
            self._assistant.start_conversation()
            self._assistant.send_text_query(message)
            self._assistant.set_mic_mute(False)

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--credentials', type=existing_file,
                        metavar='OAUTH2_CREDENTIALS_FILE',
                        default=os.path.join(
                            os.path.expanduser('~/.config'),
                            'google-oauthlib-tool',
                            'credentials.json'
                        ),
                        help='Path to store and read OAuth2 credentials')
    parser.add_argument('--device_model_id', type=str,
                        metavar='DEVICE_MODEL_ID', required=True,
                        default='assistantsdk-170114-project-diva-jy6ql4',
                        help='The device model ID registered with Google')
    parser.add_argument('--project_id', type=str, metavar='PROJECT_ID',
                        required=False,default='',
                        help='The project ID used to register device instances.')
    parser.add_argument('-v', '--version', action='version', 
                        version='%(prog)s ' + Assistant.__version_str__())
    args = parser.parse_args()            

    assistant = MyAssistant(args.credentials, args.project_id, args.device_model_id)

    assistant.start()

    while True:
        m = input()
        try:
            m = COMMANDS[m]
        except:
            pass
        assistant.send_text(m)

if __name__ == '__main__':
    main()
