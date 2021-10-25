import subprocess
import re

def _ignore_somecode(text):
    """
    Ignore new pages and CR.
    In git, these are represented as '\r' and '\f'
    If we add '\0' to database, we get error.
    """
    text = re.sub('\r', '', text)
    text = re.sub('\f', '', text)
    text = re.sub('\0', '', text)
    return text

def _content(dirname, commit_hash, file_name, lines):
    lines_str_form = ''
    for l in lines:
        lines_str_form = lines_str_form + '-L{0},+1 '.format(l)
    cmd = 'git -C {0} blame {1} -l -n {2}^ -- {3}'.format(dirname,lines_str_form,commit_hash,file_name)
    show = subprocess.check_output(cmd,shell=True).decode('utf-8', errors='ignore')
    show = _ignore_somecode(show)

    return show

def _main_git_blame(dirname, commit_hash, file_name, lines, num, num_divide):

    show = ""
    for cnt in range(num_divide):
        if cnt==num_divide-1:
            show += _content(dirname, commit_hash, file_name, lines[cnt*num:])
        else:
            show += _content(dirname, commit_hash, file_name, lines[cnt*num:(cnt+1)*num])

    return show

def git_blame(dirname, commit_hash, file_name, lines):

    num_divide = 1
    while(1):
        num = int(len(lines)/num_divide)

        try:
            show = _main_git_blame(dirname, commit_hash, file_name, lines, num, num_divide)
            break
        except:
            num_divide += 1
            continue

    return show

