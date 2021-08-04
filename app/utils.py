import os

def list_files(dirname, filter=['.json']):
    result = []
    for maindir, subdir, file_name_list in os.walk(dirname):
        for filename in file_name_list:
            apath = os.path.join(maindir, filename)
            ext = os.path.splitext(apath)[1]

            if ext in filter:
                result.append(apath)

    return result
