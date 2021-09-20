from time import sleep
from symbols import *
from run import *

import logging
logger = logging.getLogger(__name__)

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

def generate_header_tree(project_path, root_header, show_raw_graph=True, dotfile=None):
    '''
    Generate the import header tree graph for the project.
    '''

    class HeaderNode:
        all_nodes = []

        def __init__(self, name, dir=None, module=None, source=None):
            self.name = name        # header filename.
            self.dir = dir          # header file's parent path.
            self.module = module    # framework name if exists.
            self.source = source    # reference header file path.
            self.import_paths = []  # all the headers imported in current header.

        def __repr__(self):
            return f'<Node: {self.name} {self.dir or ""} {self.source and self.source.name or ""}>'

        @property
        def fullpath(self):
            return os.path.join(self.dir, self.name) if self.dir else None

        def save(self):
            self.__class__.all_nodes.append(self)

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

    all_headers = find_source_files(project_path, extensions=[], dir_filter=lambda dirname, dirpath: dirname not in ['lib', 'grpc', 'UBC'])

    # First, generate header nodes.
    for root, name in all_headers:
        created, node = HeaderNode.get_or_create(name, dir=root)

        if created:
            node.save()
        else:
            logger.warn(f'Found duplicated header file {name}')

    logger.debug(f'Total headers: {len(HeaderNode.all_nodes)}')

    if dotfile:
        import pygraphviz as pgv
        tree = pgv.AGraph(rankdir='LR')

    def analyze_header(node, depth=0):
        if show_raw_graph:
            print(f'{"    " * depth}{node.name}')

        node.analyzed = True

        for header in get_all_header_imports(node.fullpath):
            created, sub_node = HeaderNode.get_or_create(header)
            sub_node.source = node

            if created:
                sub_node.save()
                # Skip the new incoming header files.
                continue

            if sub_node.fullpath is None:
                # Skip the external header files.
                continue

            path = node.fullpath

            if path in sub_node.import_paths:
                continue

            sub_node.import_paths.append(path)
            sub_node.save()

            if dotfile:
                tree.add_edge(node.name, sub_node.name)

            # Third, loop into to build the source relationship.
            analyze_header(sub_node, depth + 1)

    # Second, start scanning from the specified root header.
    root_node = HeaderNode(os.path.basename(root_header), dir=os.path.dirname(root_header))
    root_node.save()
    analyze_header(root_node)

    # Finally, generate tree with graphviz if necessary.
    if dotfile:
        tree.write(dotfile)
