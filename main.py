#!/usr/bin/env python

import logging, logging.config, coloredlogs
import os.path
from symbols import *
from analyze import *

logging.config.fileConfig('logging.conf')
coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__file__)

def print_all_unused_import(project_path):
    for symbol, filepath, results in get_all_unused_code_import(project_path):
        logger.info(f'Found unused symbol {symbol} in \n{filepath} with {len(results)} result(s):\n{".".join(results)}\n')

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
