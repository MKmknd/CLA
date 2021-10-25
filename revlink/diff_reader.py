# -*- coding: utf-8 -*-

import re
import pickle
import sys

from revlink import git_reader


"""
Identify whether the change fix source code
"""
def remove_linefeedcode(text):
    text = re.sub('\r', '', text)
    text = re.sub('\n', '', text)
    return text


def isChanged(repo_dir, prev_hash, curr_hash):
    """Identify changes which only fix newlines"""
    prev_code = remove_linefeedcode(git_reader.git_show_module_without_comment(repo_dir, prev_hash))
    curr_code = remove_linefeedcode(git_reader.git_show_module_without_comment(repo_dir, curr_hash))
    if prev_code != curr_code:
        return True
    else:
        return False


def isMeaningfulChange(repo_dir, file_hash, linenums):
    """Using files and line numbers to indeitfy whether the change
    includes parts of source code"""
    source_code = git_reader.git_show_module_without_comment(repo_dir, file_hash)
    lines = source_code.splitlines()
    lines.insert(0, '')
    for i in linenums:
        #print("{0}: {1}".format(i, lines[i]))
        if not re.match('^\s*$', lines[i]):  # If a list of the line numbers includes source code,
            return True
    return False


def isMeaningfulFile(name):
    """check extentions"""
    #e_list = ['java', 'c', 'h', 'cpp', 'cxx', 'hpp', 'hxx']
    #e_list = ['java', 'c']
    e_list = ['java']
    for extention in e_list:
        if re.search('\.{}$'.format(extention), name):
            return True
    return False


"""
Return file hashs
"""
def find_filehash(module_info):
    for line in module_info.splitlines():
        try:
            if 'index' in line:
                match = re.search('index[\s]([\w]+)\.\.([\w]+)[\s]?', line)
                prev_hash = match.group(1)
                curr_hash = match.group(2)
                return prev_hash, curr_hash
        except Exception:
            print(line)
    exit('Error: index should exists')


"""
Extract file name (after changed)
"""
def find_moduleName(module):
    re_moduleName = re.compile('^\+\+\+[\s]b?/(.+)$')
    for line in module.splitlines():
        match = re_moduleName.match(line)
        if match:
            return match.group(1)
    raise

"""
Extract file name (before changed)
"""
def find_moduleName_before(module):
    re_moduleName = re.compile('^\-\-\-[\s]a?/(.+)$')
    for line in module.splitlines():
        match = re_moduleName.match(line)
        if match:
            return match.group(1)
    raise


"""
Extract diff information
"""
def split_diff_bymodule(git_show):
    modulediff_list = []
    modules = re.split('\ndiff[\s]--git[\s]a/.+\n', git_show) # split a patch of git show into two parts.
    del(modules[0])  # Remove the first part which is above of a commit message
    for module in modules:
        try:
            module_name = find_moduleName(module)
            module_name_before = find_moduleName_before(module)
        except Exception:  # If the change is only change the modulename, we ignore the change
            # Example: old mode 100755 new mode 100644
            # If we want to remedy this problem, we can use "git config core.filemode false" in git config
            # print('module name is not found.', file=sys.stderr)
            # print("[MODULE]\n" + module + "\n", file=sys.stderr)
            continue
        if not isMeaningfulFile(module_name):  # Check extentions
            continue
        module_info, module_diff = re.split('\n\+\+\+[\s]b/.+\n', module)
        prev_hash, curr_hash = find_filehash(module_info)
        modulediff_list.append([module_name, prev_hash, curr_hash, module_diff, module_name_before])
    # for module in modules_withName:
    #     print('########')
    #     print(module[0], module[1])
    #     print(module[2])
    #     print('########')

    #print("DISPLAY")
    #print(git_show)
    #print("")
    #print("===")
    #print("")
    #for module in modulediff_list:
    #    print(module)
    #sys.exit()
    return modulediff_list


def find_functionName(line):
    re_functionName = re.compile('^@@[\s]-\d+.+\+\d+.*[\s]@@[\s](.*$)')
    re_globalName = re.compile('^@@[\s]-\d+.+\+\d+.*[\s]@@$')
    # These regular expressions are matched with "b/path/to/file" and "/dev/null".
    # The ignored files--such as .txt and null--are removed in 'split_intoModule()'.
    match = re_functionName.match(line)
    if match:
        return match.group(1)
    else:
        match = re_globalName.match(line)
        if match:
            return 'Global'
        else:
            return None

    print("ERROR in find_functionName")
    sys.exit()


def search_lines(module_diff):
    #print("\nContext\n")
    re_lineInfo = re.compile('^@@[\s]-(\d+).+\+(\d+)')
    re_deletedLine = re.compile('^-')
    re_addedLine = re.compile('^\+')
    deleted_nums = []
    added_nums = []
    del_start, del_offset = 0, 0  # Deleted lines only consider line numbers in "previous" commits.
    add_start, add_offset = 0, 0  # Added lines only consider line numbers in "present" commits.

    functionName = ''
    deleted_nums_with_functionName = {}
    added_nums_with_functionName = {}

    for line in module_diff.splitlines():

        tempFunctionName = find_functionName(line)
        if tempFunctionName is not None:
            functionName = tempFunctionName
            if functionName not in deleted_nums_with_functionName:
                deleted_nums_with_functionName[functionName] = []
            if functionName not in added_nums_with_functionName:
                added_nums_with_functionName[functionName] = []

        match = re_lineInfo.match(line)
        if match:
            del_start = int(match.group(1))
            add_start = int(match.group(2))
            add_offset, del_offset = 0, 0
            continue
        if '\ No newline at end of file' == line:
            continue  # for no newline
        if re_deletedLine.match(line):
            deleted_nums.append(del_start + del_offset)
            deleted_nums_with_functionName[functionName].append(del_start + del_offset)
            del_offset = del_offset + 1
        elif re_addedLine.match(line):
            added_nums.append(add_start + add_offset)
            added_nums_with_functionName[functionName].append(add_start + add_offset)
            add_offset = add_offset + 1
        else:
            add_offset = add_offset + 1
            del_offset = del_offset + 1



    return added_nums, deleted_nums, deleted_nums_with_functionName, added_nums_with_functionName


def collect_diffcode_metrics(commit_hash, repo_dir):
    """
    Extract git show data.
    """
    show = git_reader.git_show_with_context(repo_dir, commit_hash, 0)
    modulediff_list = split_diff_bymodule(show)
    diffcode_metrics = []
    for module_data in modulediff_list:
        module_name, prev_hash, curr_hash, module_diff, module_name_before = module_data
        added, deleted, deleted_nums_with_functionName, added_nums_with_functionName = search_lines(module_diff)
        diffcode_metrics.append({
            'module_name': module_name,
            'module_name_before': module_name_before,
            'added': added,
            'deleted': deleted,
            'prev': prev_hash,
            'curr': curr_hash
            })
            #'deleted_nums_with_functionName': deleted_nums_with_functionName,
            #'added_nums_with_functionName': added_nums_with_functionName
            #})
    return diffcode_metrics


def search_tokens(module_diff):
    #print("\nContext\n")
    re_lineInfo = re.compile('^@@[\s]-(\d+).+\+(\d+)')
    re_deletedLine = re.compile('^-')
    re_addedLine = re.compile('^\+')
    deleted_tokens = []
    added_tokens = []
    deleted_type = []
    added_type = []
    del_start, del_offset = 0, 0  # Deleted lines only consider line numbers in "previous" commits.
    add_start, add_offset = 0, 0  # Added lines only consider line numbers in "present" commits.

    for line in module_diff.splitlines():
        #print(line)

        match = re_lineInfo.match(line)
        if match:
            del_start = int(match.group(1))
            add_start = int(match.group(2))
            add_offset, del_offset = 0, 0
            continue
        if '\ No newline at end of file' == line:
            continue  # for no newline
        if re_deletedLine.match(line):
            deleted_type.append(line.split("|")[0])
            deleted_tokens.append("-" + "|".join(line.split("|")[1:]))
            del_offset = del_offset + 1
        elif re_addedLine.match(line):
            added_type.append(line.split("|")[0])
            added_tokens.append("+" + "|".join(line.split("|")[1:]))
            add_offset = add_offset + 1
        else:
            add_offset = add_offset + 1
            del_offset = del_offset + 1



    return added_tokens, deleted_tokens, added_type, deleted_type

def collect_diffcode_tokens(commit_hash, repo_dir):
    """
    Extract git show data.
    """
    show = git_reader.git_show_with_context(repo_dir, commit_hash, 0)
    show = git_reader.replace_comment_viewrepo_show_output(show)
    modulediff_list = split_diff_bymodule(show)
    diffcode_metrics = []
    for module_data in modulediff_list:
        module_name, prev_hash, curr_hash, module_diff, module_name_before = module_data
        added, deleted, added_type, deleted_type = search_tokens(module_diff)
        diffcode_metrics.append({
            'module_name': module_name,
            'module_name_before': module_name_before,
            'added': added,
            'deleted': deleted,
            'added_type': added_type,
            'deleted_type': deleted_type,
            'prev': prev_hash,
            'curr': curr_hash
            })
    return diffcode_metrics

