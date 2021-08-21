from time import sleep
from symbols import *
from run import *

import logging
logger = logging.getLogger()

def check_unused_import(project_path):
    '''
    Analyze all the header imports is necessary or not, remove the unused ones with git-commit
    after validating via xcodebuild.
    '''
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

def generate_header_tree(project_path, root_header):
    '''
    Generate the import header tree graph for the project.
    '''

    class HeaderNode:
        all_nodes = []

        def __init__(self, name, dir=None, module=None, source=None):
            self.name = name
            self.dir = dir
            self.module = module
            self.source = source
            self.import_paths = []

            self.__class__.all_nodes.append(self)

        def __repr__(self):
            return f'<Node: {self.name} {self.dir or ""} {self.source or ""}>'

        @property
        def fullpath(self):
            return os.path.join(self.dir, self.name) if self.dir else None

        @classmethod
        def find_by_name(cls, name, dir=None):
            nodes = list(filter(lambda x: x.name == name and (dir is None or x.dir == dir), cls.all_nodes))
            return nodes[0] if len(nodes) > 0 else None

        @classmethod
        def get_or_create(cls, name, dir=None):
            node = cls.find_by_name(name, dir)

            if node:
                return False, node
            else:
                return True, HeaderNode(name, dir=dir)

    for root, name in find_source_files(project_path, extensions=[]):
        created, node = HeaderNode.get_or_create(name, dir=root)

        if not created:
            logger.warn(f'Found duplicated header file {name}')

    # logger.debug(f'Headers: \n{HeaderNode.all_nodes}\nIn total: {len(HeaderNode.all_nodes)}')

    def analyze_header(node, depth, source=None):
        print(f'{"    " * depth}{node.name}')
        node.analyzed = True

        for header in get_all_header_imports(node.fullpath):
            created, sub_node = HeaderNode.get_or_create(header)
            sub_node.source = node

            if created:
                # Skip the new incoming header files.
                continue

            if sub_node.fullpath is None:
                # Skip the external header files.
                continue

            signature = node.fullpath

            if signature in sub_node.import_paths:
                continue

            sub_node.import_paths.append(signature)
            analyze_header(sub_node, depth + 1)

    root_node = HeaderNode(os.path.basename(root_header), dir=os.path.dirname(root_header))
    analyze_header(root_node, 0)

