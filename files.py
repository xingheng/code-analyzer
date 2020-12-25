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

            yield (root, name)

def find_source_files(dir, include_headers=True):
    'Return all the source files under the specified directory.'

    def directory_filter(dirname, dirpath):
        return dirname not in ['.git', 'Pods', 'lib']

    def file_filter(filename, dirpath):
        _, ext = os.path.splitext(filename)
        expected_exts = ['.m', '.mm']

        if include_headers:
            expected_exts.append('.h')

        return ext in expected_exts

    return find_files(dir, dir_filter=directory_filter, file_filter=file_filter)
