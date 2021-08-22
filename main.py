#!/usr/bin/env python

import logging, logging.config, coloredlogs
import os.path
import click
from symbols import *
from analyze import *

# Refer to
#   1. https://stackoverflow.com/a/7507842/1677041
#   2. https://stackoverflow.com/a/49400680/1677041
#   3. https://docs.python.org/2/library/logging.config.html
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'colored': {
            '()': 'coloredlogs.ColoredFormatter',
            'format': "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            'datefmt': '%H:%M:%S',
        }
    },
    'handlers': {
        'default': {
            'level': 'DEBUG' if __debug__ else 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
        'console': {
            'level': 'DEBUG' if __debug__ else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
        '__main__': {  # if __name__ == '__main__'
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable logger level to DEBUG')
@click.pass_context
def cli(ctx, debug):
    logger.setLevel(logging.DEBUG if debug else logging.WARNING)
    debug and click.echo('Debug mode is on')


@cli.command()
@click.argument('project', envvar='PROJECT', type=click.Path(exists=True, file_okay=False))
@click.option('--show-count/--hide-count', default=True, help='Show total count or not.')
@click.pass_context
def get_all_vcs(ctx, project, show_count):
    '''
    Output all the view controllers from the project.
    '''
    all_vcs = get_all_view_controllers(project)

    for result in all_vcs:
        print(f'@"{result}", ')

    show_count and print(len(all_vcs))

@cli.command()
@click.argument('project', envvar='PROJECT', type=click.Path(exists=True, file_okay=False))
@click.option('--show-count/--hide-count', default=True, help='Show total count or not.')
@click.pass_context
def analyze_unused_symbols(ctx, project, show_count):
    '''
    Analyze all the unused symbols from the project. FYI.
    '''

    for symbol, filepath, results in get_all_unused_code_import(project):
        logger.info(f'Found unused symbol {symbol} in \n{filepath} with {len(results)} result(s):\n{".".join(results)}\n')

@cli.command()
@click.argument('project', envvar='PROJECT', type=click.Path(exists=True, file_okay=False))
@click.option('--show-count/--hide-count', default=True, help='Show total count or not.')
@click.pass_context
def analyze_unused_vc_imports(ctx, project, show_count):
    '''
    Analyze all the unused view controller's imports from the project. FYI.
    '''

    all_vcs = get_all_view_controllers(project)

    for vc in all_vcs:
        print(f'Analyzing {vc}')
        get_unused_symbol_code_import(vc, project)

@cli.command()
@click.argument('project', envvar='PROJECT', type=click.Path(exists=True, file_okay=False))
@click.argument('entry', envvar='ENTRY_HEADER', type=click.Path(exists=True, dir_okay=False))
@click.option('--raw-result/--hide-raw-result', default=True, help='Show raw graph in stdout or not.')
@click.option('--dot-file', type=click.Path(dir_okay=False), default=None, help='Generate the graphviz result to the dot file.')
@click.pass_context
def generate_header_graph(ctx, project, entry, raw_result, dot_file):
    '''
    Generate all the headers import graph with specified project and header entry.
    '''
    project_dir = os.path.expanduser(project)
    pch_header = os.path.join(project, entry)

    generate_header_tree(project_dir, pch_header, show_raw_graph=raw_result, dotfile=dot_file)


if __name__ == '__main__':
    cli()
