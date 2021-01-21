import re
from files import *

def search_file_with_regex(regex, filepath):
    'Search regex in specified file content.'
    with open(filepath, 'r') as f:
        content = f.read()
        return re.findall(regex, content, flags=re.M|re.U)

    return []

def search_target_in_project(regex, project_path, flat=True, mapper=None):
    'Search regex in all the source file under the specified project path.'
    for dirpath, filename in find_source_files(project_path):
        filepath = os.path.join(dirpath, filename)
        results = search_file_with_regex(regex, filepath)

        if len(results) <= 0:
            continue

        if flat:
            for result in results:
                yield (filepath, mapper(result))
        else:
            yield (filepath, list(map(mapper, results) if mapper else results))

def search_all_view_controllers(project_path, flat=True):
    'Search all the view controllers\' usages under the project.'
    regex = r'@interface\s+SRT\w+ViewController.*:.*SRTBaseViewController'

    def get_vc_name(definition):
        units = re.split('@interface|:', definition)
        return units[1].lstrip().rstrip()

    return search_target_in_project(regex, project_path, flat, mapper=get_vc_name)

def get_all_view_controllers(project_path):
    'Return all the unique view controller names under the project.'
    all_vcs = list()

    for _, results in search_all_view_controllers(project_path, flat=False):
        all_vcs.extend(results)

    return sorted(list(set(all_vcs)))

def search_all_classes(project_path):
    'Search all the class\' usages under the project.'
    regex = r'@interface\s+\w+.*:.*\w+'

    def get_class_name(definition):
        units = re.split('@interface|:', definition)
        return units[1].lstrip().rstrip()

    return search_target_in_project(regex, project_path, False, mapper=get_class_name)

def get_all_classes(project_path):
    'Return all the unique class names under the project.'
    all_classes = list()

    for _, results in search_all_classes(project_path):
        all_classes.extend(results)

    return sorted(list(set(all_classes)))


def is_code_import(content):
    'Whether the source content is a #import "" or #import <>.'
    return re.match(r'#import.*[<"]\w+\.h[<"]', content, flags=re.M) is not None

def is_code_single_line_comment(content):
    'Whether the source content is a single line comment likes //'
    return re.match(r'^\s*//.*', content, flags=re.M) is not None


def get_unused_symbol_code_import(symbol_name, project_path):
    'Return the specified symbol\'s import and comment usages under the project.'
    regex = r'^.*%s.*$' % symbol_name

    for filepath, results in search_target_in_project(regex, project_path, flat=False):
        if symbol_name in filepath:
            # Skip the symbol file itself.
            continue

        is_unused = True

        for result in results:
            is_unused &= is_code_import(result) or is_code_single_line_comment(result)

        if is_unused:
            yield (filepath, results)

def get_all_unused_code_import(project_path):
    'Return all the unused import or comment view controller usages under the project'
    for symbol in get_all_view_controllers(project_path):
        for filepath, results in get_unused_symbol_code_import(symbol, project_path):
            yield (symbol, filepath, results)
