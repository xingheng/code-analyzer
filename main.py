#!/usr/bin/env python

import logging, logging.config, coloredlogs
import os.path
from time import sleep
from symbols import *
from run import *

logging.config.fileConfig('logging.conf')
coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__)

def print_all_unused_import(project_path):
    for symbol, filepath, results in get_all_unused_code_import(project_path):
        logger.info(f'Found unused symbol {symbol} in \n{filepath} with {len(results)} result(s):\n{".".join(results)}\n')

def check_unused_import(project_path):
    workspace = find_xcode_workspace(project_path)
    _, workspace_name = os.path.split(workspace)
    # Take the workspace prefix as default scheme name
    scheme, _ = os.path.splitext(workspace_name)

    def output(message):
        # print(message, flush=True, end='')
        print('.', flush=True, end='')

    logger.info('Validating project environment before checking.')

    if not run_xcode_build(workspace, scheme, output_handler=output):
        logger.error(f'Make sure the project {project_path} could build successfully before validating!')
        return

    whitelist_filenames = [
        'shiritan-Bridging-Header.h',
        'SRTConfig.h',
        'shiritanTests.m',
        'shiritan_Tests.m',
        'shiritan_UITests.m',
    ]

    all_symbols = get_all_classes(project_path)
    unused_count, mischeck_count = 0, 0

    for idx in range(len(all_symbols)):
        symbol = all_symbols[idx]
        logger.info(f'Analyzing {symbol} ({idx}/{len(all_symbols)})')
        found_unused = False

        changes = run_git_status(project_path)

        if changes and len(changes) > 0:
            run_git_add_all(project_path) and run_git_commit(project_path)

        for filepath, results in get_unused_symbol_code_import(symbol, project_path):
            _, filename = os.path.split(filepath)

            if filename in whitelist_filenames:
                continue

            if symbol in filepath:
                # Skip the symbol file itself.
                continue

            is_unused = True

            for result in results:
                is_unused &= is_code_import(result)# or is_code_single_line_comment(result)

            if not is_unused:
                continue

            logger.info(f'{symbol} is unused in file {filepath}!')

            for r in results:
                logger.info(f'\n{r}')

                if remove_line_from_file(filepath, r):
                    logger.info('Validating...')

                    if run_xcode_build(workspace, scheme, output_handler=output):
                        run_git_add_all(project_path)
                        logger.info(f'Validated successfully! Removed line "{r}" from file {filepath}.')
                        found_unused = True
                        unused_count += 1
                    else:
                        run_git_discard(project_path)
                        logger.info(f'Validated failed! Revert line "{r}" from file {filepath}.')
                        mischeck_count += 1

                    logger.info('Let the cpu sleep a while. :)')
                    sleep(10)

        if found_unused:
            run_git_commit(project_path, f'{symbol} usages.')

    logger.info(f'Removed unused {unused_count} change(s), mischeck {mischeck_count}')


def main():
    project_dir = os.path.expanduser('~/work/butter-cam/projects/shiritan')

    # all_vcs = get_all_view_controllers(project_dir)
    # # logger.debug(all_vcs)
    # logger.debug(len(all_vcs))

    # for result in all_vcs:
    #     print(f'@"{result}", ')

    # print_all_unused_import(project_dir)
    # for vc in all_vcs:
    #     print(f'Analyzing {vc}')
    #     get_unused_symbol_code_import(vc, project_dir)

    check_unused_import(project_dir)

if __name__ == '__main__':
    main()
