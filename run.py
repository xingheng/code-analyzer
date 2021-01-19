import subprocess
import pty
import os, os.path
import distutils.spawn

from datetime import datetime
from time import time

import logging
logger = logging.getLogger(__file__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.path.exists(OUTPUT_DIR) or os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_xcode_build(workspace, scheme, output_dir=None):
    '''
    Run task in a sub-process.

    References:
    https://stackoverflow.com/a/12471855/1677041
    https://stackoverflow.com/a/28925318/1677041
    '''

    cur_time = datetime.fromtimestamp(time()).strftime('%Y%m%d-%H%M%S-%f')
    fout_path = os.path.join(output_dir or OUTPUT_DIR, f'output-{cur_time}.log')
    foutput = open(fout_path, 'wb')

    cmd = f'''
        set -euo pipefail

        if [ -x "$(command -v xcpretty)" ]; then
            /usr/bin/xcodebuild -workspace "{workspace}" -scheme "{scheme}" -arch x86_64 clean build | xcpretty
        else
            /usr/bin/xcodebuild -workspace "{workspace}" -scheme "{scheme}" -arch x86_64 clean build;
            echo "xcpretty is not installed, suggest to install it and try again.";
        fi
    '''

    try:
        master, slave = pty.openpty() # provide tty to enable line-buffering for sub-process.
        p = subprocess.Popen(['/bin/sh', '-c', cmd], stdout=slave, stderr=slave, close_fds=True)

        # Close the slave descriptor! otherwise we will hang forever waiting for input.
        os.close(slave)

        def read(fd):
            try:
                while True:
                    buffer = os.read(fd, 1024)
                    if not buffer:
                        return

                    yield buffer

            # Unfortunately with a pty, an IOError will be thrown at EOF.
            # On Python 2, OSError will be thrown instead.
            except (IOError, OSError) as e:
                pass

        for buffer in read(master):
            foutput.write(buffer)
            # logger.info(buffer.decode('utf-8'))
            print(buffer.decode('utf-8'), flush=True)
            # print('.', end='', flush=True)

        ret_code = p.poll()

        if ret_code == 0:
            logger.info('Completed!')
        else:
            if ret_code < 0:
                logger.warning(f'Killed by signal {ret_code}')

            logger.warning(f'Completed with error! Code is {ret_code}')

        logger.info(f'Check the task result under the path {fout_path}')

        result = ret_code == 0
    except subprocess.CalledProcessError as e:
        logger.exception(f'Exception:\ncode:{e.returncode}\noutput:{e.output}')
        result = False
    finally:
        foutput.close()

    return result


def run_git_command(git_repo, command):
    '''Run sub-command in the specified git repsitory.'''

    executable = distutils.spawn.find_executable('git')

    if executable is None:
        logger.error('git is missing in the envionment paths!')
        return -1, None, None

    try:
        cmd = f'{executable} -C "{git_repo}" {command}'
        p = subprocess.Popen(['/bin/sh', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        ret_code = p.wait()
        output, error = p.stdout.read().decode('utf-8'), p.stderr.read().decode('utf-8')

        return ret_code, output, error
    except Exception as e:
        logger.exception(e)

    return -1, None, None

def run_git_status(git_repo):
    ret_code, output, error = run_git_command(git_repo, 'status --porcelain=v1')

    if ret_code == 0:
        if not output:
            return None

        # https://git-scm.com/docs/git-status
        file_list = []

        for line in output.splitlines():
            # Get the relative file path
            path = line[3:]
            # Use the the new file path if rename/copy mode exists
            idx = path.find('->')
            if idx != -1:
                path = path[idx + 2:]
            # Strip the quoted string literal if whitespace or other nonprintable characters exist
            path = path.strip(' "\'')
            # Convert to the full file path
            path = os.path.abspath(os.path.join(git_repo, path))

            if os.path.exists(path):
                file_list.append(path)
            else:
                logger.warning('Found invalid path: %s, skipping it!' % path)

        return file_list
    else:
        logger.error(f'Error: {error}')

    return None

def run_git_add_all(git_repo):
    'git: add all the unstaged files to staged.'
    ret_code, _, _ = run_git_command(git_repo, 'add -A .')
    return ret_code == 0

def run_git_discard(git_repo):
    'git: discard all the unstaged file\'s changes.'
    ret_code, _, _ = run_git_command(git_repo, f'checkout -- .')
    return ret_code == 0

def run_git_commit(git_repo, message=None):
    'git: commit all the staged files.'
    message = message or str(datetime.now())
    ret_code, _, _ = run_git_command(git_repo, f'commit --allow-empty -m "bot: {message}"')
    return ret_code == 0
