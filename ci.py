#!/usr/bin/env python

# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

from __future__ import print_function

import os
import signal
import subprocess
import sys


class SubprocessException(Exception):
    pass


def get_changed_files():
    commit_range = os.environ.get('TRAVIS_COMMIT_RANGE', None)
    if not commit_range:
        return []

    p = subprocess.Popen([
        'git', 'diff', '--name-only', commit_range
    ], stdout=subprocess.PIPE)

    stdout, _ = p.communicate()
    if p.returncode != 0:
        raise SubprocessException('git returned non-zero exit code')

    return [line.strip() for line in stdout.splitlines()]


def get_dirty_modules(dirty_files):
    dirty = set()
    for f in dirty_files:
        if os.path.sep in f:
            mod, _ = f.split(os.path.sep, 1)

            if not os.path.exists(os.path.join(mod, 'Chart.yaml')):
                continue

            dirty.add(mod)

    return list(dirty)


def get_dirty_for_module(files, module=None):
    ret = []
    print(files)
    for f in files:
        if os.path.sep in f:
            mod, rel_path = f.split(os.path.sep, 1)
            if mod == module:
                ret.append(rel_path)
        else:
            # top-level file, no module
            if module is None:
                ret.append(f)

    return ret


def run_verify(modules):
    build_args = ['helm', 'lint'] + modules

    print('verify command:', build_args)

    p = subprocess.Popen(build_args, stdin=subprocess.PIPE)

    def kill(signal, frame):
        p.kill()
        print()
        print('killed!')
        sys.exit(1)

    signal.signal(signal.SIGINT, kill)
    if p.wait() != 0:
        print('lint failed, exiting!')
        sys.exit(p.returncode)


# def run_push(modules):
#     if os.environ.get('TRAVIS_SECURE_ENV_VARS', None) != "true":
#         print('No push permissions in this context, skipping!')
#         print('Not pushing: %r' % modules)
#         return
#
#     username = os.environ.get('DOCKER_HUB_USERNAME', None)
#     password = os.environ.get('DOCKER_HUB_PASSWORD', None)
#     if username and password:
#         print('Logging into docker registry...')
#         r = subprocess.call([
#             'docker', 'login',
#             '-u', username,
#             '-p', password
#         ])
#         if r != 0:
#             print('Docker registry login failed, cannot push!')
#             sys.exit(1)
#
#     push_args = ['dbuild', '-sd', 'build', 'push', 'all'] + modules
#     print('push command:', push_args)
#
#     p = subprocess.Popen(push_args, stdin=subprocess.PIPE)
#
#     def kill(signal, frame):
#         p.kill()
#         print()
#         print('killed!')
#         sys.exit(1)
#
#     signal.signal(signal.SIGINT, kill)
#     if p.wait() != 0:
#         print('build failed, exiting!')
#         sys.exit(p.returncode)

def handle_pull_request(files, modules):
    if os.environ.get('TRAVIS_BRANCH', None) != 'master':
        print('Not master branch, skipping tests.')
        return

    if modules:
        run_verify(modules)
    else:
        print('No modules to verify.')

    for module in modules:
        print (get_dirty_for_module(files, module))

def handle_push(files, modules):
    if os.environ.get('TRAVIS_BRANCH', None) != 'master':
        print('Not master branch, skipping tests.')
        return

    if modules:
        run_verify(modules)
    else:
        print('No modules to verify.')
        return

    modules_to_push = []

    for module in modules:
        dirty = get_dirty_for_module(files, module)

        if 'Chart.yaml' in dirty:
            modules_to_push.append(module)

    # if modules_to_push:
    #     run_push(modules)
    # else:
    #     print('No modules to push.')
    #
    # if modules_to_readme:
    #     run_readme(modules)
    # else:
    #     print('No READMEs to update.')


def handle_other(files, modules, tags):
    print('Unsupported event type "%s", nothing to do.' % (
        os.environ.get('TRAVS_EVENT_TYPE')))


def main():
    print('Environment details:')
    print('TRAVIS_COMMIT=', os.environ.get('TRAVIS_COMMIT'))
    print('TRAVIS_COMMIT_RANGE=', os.environ.get('TRAVIS_COMMIT_RANGE'))
    print('TRAVIS_PULL_REQUEST=', os.environ.get('TRAVIS_PULL_REQUEST'))
    print('TRAVIS_PULL_REQUEST_SHA=',
          os.environ.get('TRAVIS_PULL_REQUEST_SHA'))
    print('TRAVIS_PULL_REQUEST_SLUG=',
          os.environ.get('TRAVIS_PULL_REQUEST_SLUG'))
    print('TRAVIS_SECURE_ENV_VARS=', os.environ.get('TRAVIS_SECURE_ENV_VARS'))
    print('TRAVIS_EVENT_TYPE=', os.environ.get('TRAVIS_EVENT_TYPE'))
    print('TRAVIS_BRANCH=', os.environ.get('TRAVIS_BRANCH'))
    print('TRAVIS_PULL_REQUEST_BRANCH=',
          os.environ.get('TRAVIS_PULL_REQUEST_BRANCH'))
    print('TRAVIS_TAG=', os.environ.get('TRAVIS_TAG'))
    print('TRAVIS_COMMIT_MESSAGE=', os.environ.get('TRAVIS_COMMIT_MESSAGE'))

    files = get_changed_files()
    modules = get_dirty_modules(files)
    # tags = get_message_tags()

    # if tags:
    #     print('Tags detected:')
    #     for tag in tags:
    #         print('  ', tag)
    # else:
    #     print('No tags detected.')

    func = {
        'pull_request': handle_pull_request,
        'push': handle_push
    }.get(os.environ.get('TRAVIS_EVENT_TYPE', None), handle_other)

    func(files, modules)


if __name__ == '__main__':
    main()
