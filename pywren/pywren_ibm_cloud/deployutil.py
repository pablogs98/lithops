#
# (C) Copyright IBM Corp. 2018
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
#

import os
import sys
from pywren_ibm_cloud import wrenconfig
from pywren_ibm_cloud.storage import storage
from pywren_ibm_cloud.cf_connector import CloudFunctions
from pywren_ibm_cloud.wrenconfig import CF_ACTION_NAME_DEFAULT

def create_zip_action():
    print('Creating action zip...')

    if not os.path.isfile('../pywren/__main__.py'):
        os.symlink('../pywren/pywren_ibm_cloud/action/__main__.py', '../pywren/__main__.py')
    cmd = 'cd ../pywren; zip -FSr ../runtime/ibmcf_pywren.zip __main__.py pywren_ibm_cloud/ -x "*__pycache__*"'
    res = os.system(cmd)
    if res != 0:
        exit()
    os.remove('../pywren/__main__.py')


def extract_modules(image_name, config = None):
    # Extract installed Python modules from docker image
    # And store them into storage

    # Create runtime_name from image_name
    username, appname = image_name.split('/')
    runtime_name = appname.replace(':', '_')

    # Load PyWren config from ~/.pywren_config
    if config is None:
        config = wrenconfig.default()
    else:
        config = wrenconfig.default(config)

    # Create storage_handler to upload modules file
    storage_config = wrenconfig.extract_storage_config(config)
    internal_storage = storage.InternalStorage(storage_config)

    print('Creating and uploading modules file...')

    sys.stdout = open(os.devnull, 'w')
    with open("extract_modules.py", "r") as action_py:
        action_code = action_py.read()
    cf_client = CloudFunctions(config['ibm_cf'])
    action_name = runtime_name+'_modules'
    cf_client.create_action(action_name, memory=512, timeout=300000,
                            code=action_code, kind='blackbox',
                            image=image_name, is_binary=False)

    runtime_meta = cf_client.invoke_with_result(action_name)
    internal_storage.put_runtime_info(runtime_name, runtime_meta)
    cf_client.delete_action(action_name)
    sys.stdout = sys.__stdout__


def create_blackbox_runtime(image_name, config = None):
    # Create runtime_name from image_name
    username, appname = image_name.split('/')
    runtime_name = appname.replace(':', '_')

    # Load PyWren config from ~/.pywren_config
    if config is None:
        config = wrenconfig.default()
    else:
        config = wrenconfig.default(config)

    # Upload zipped PyWren action
    print('Uploading action...')
    with open("ibmcf_pywren.zip", "rb") as action_zip:
        action_bin = action_zip.read()
        cf_client = CloudFunctions(config['ibm_cf'])
        cf_client.create_action(runtime_name, memory=2048, timeout=600000,
                                code=action_bin, kind='blackbox', image=image_name)

def clone_runtime(image_name, config = None):

    print('Cloning docker image {}'.format(image_name))
    create_zip_action()
    create_blackbox_runtime(image_name, config)
    extract_modules(image_name, config)

    print('All done!')

def default():
    print('Updating runtime {}'.format(CF_ACTION_NAME_DEFAULT))
    config = wrenconfig.default()

    # Create zipped PyWren action
    create_zip_action()

    # Upload zipped PyWren action
    print('Uploading action')
    with open("ibmcf_pywren.zip", "rb") as action_zip:
        action_bin = action_zip.read()
        cf_client = CloudFunctions(config['ibm_cf'])
        runtime_name = CF_ACTION_NAME_DEFAULT
        cf_client.create_action(runtime_name, memory=2048, timeout=600000, code=action_bin)

