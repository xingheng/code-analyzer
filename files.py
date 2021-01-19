import os, os.path

def find_files(dirpath, dir_filter=None, file_filter=None):
    'Filter all the files with directory and file filters.'
    for root, dirs, files in os.walk(dirpath):
        for name in dirs:
            if dir_filter and not dir_filter(name, root):
                dirs.remove(name)

        for name in files:
            if file_filter and not file_filter(name, root):
                continue

            yield root, name

def find_directories(dirpath, dir_filter=None):
    'Filter all the files with directory and file filters.'
    for root, dirs, _ in os.walk(dirpath):
        for name in dirs:
            if dir_filter(name, root):
                if (yield root, name) is True:
                    break
        else:
            continue
        break

def find_source_files(dir, include_headers=True):
    'Return all the source files under the specified directory.'
    expected_exts = ['.m', '.mm']

    if include_headers:
        expected_exts.append('.h')

    def directory_filter(dirname, dirpath):
        return dirname not in ['.git', 'Pods', 'lib']

    def file_filter(filename, dirpath):
        _, ext = os.path.splitext(filename)
        return ext in expected_exts

    return find_files(dir, dir_filter=directory_filter, file_filter=file_filter)

def find_xcode_workspace(dir):
    'Find the first matched xcode workspace file\' fullpath.'

    def dir_filter(dirname, parent_dirpath):
        return dirname.endswith('.xcworkspace')

    iterator = find_directories(dir, dir_filter=dir_filter)

    try:
        dirpath, filename = next(iterator)

        if dirpath and filename:
            return os.path.join(dirpath, filename)
    except StopIteration:
        pass

    return None

def remove_line_from_file(filepath, content):
    'Remove specified line content from the file.'

    result = False

    if not content.endswith('\n'):
        content += '\n'

    with open(filepath, "r+") as f:
        lines = f.readlines()
        f.seek(0)

        for line in lines:
            if line != content:
                f.write(line)
            else:
                result = True

        f.truncate()

    return result
