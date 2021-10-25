
import subprocess
import sys
import re
from datetime import datetime as dt

re_comment_repoview = re.compile('^(begin_comment|comment|end_comment).*$')

def replace_comment_viewrepo(text):
    if len(text) > 0 and text[-1] != '\n':
        text = text + '\n'  # When'\ No newline at end of file', the line number is decreased. Hence, we add one newline

    #text = re_comment_repoview.sub(repl, text)
    new_text = ""
    for line in text.splitlines():
        new_text += re_comment_repoview.sub("", line)
        new_text += "\n"
    return new_text

def ignore_somecode(text):
    """
    Ignore new pages and CR.
    In git, these are represented as '\r' and '\f'
    If we add '\0' to database, we get error.
    """
    text = re.sub('\r', '', text)
    text = re.sub('\f', '', text)
    text = re.sub('\0', '', text)
    return text

def git_show_module_without_comment(dirname, file_hash):
    try:
        text = subprocess.check_output(
                ['git', '-C', '{}'.format(dirname), 'show', file_hash],
                ).decode('utf-8', errors='ignore')
    except Exception:
        exit('Decode error.')
    text = ignore_somecode(text)
    text = replace_comment_viewrepo(text)  # remove comment
    return text

def git_show_with_context(dirname, commit_hash, context):
    show = subprocess.check_output(
            ['git', '-C', '{}'.format(dirname), 'show',
             '--unified={0}'.format(context), commit_hash],
            ).decode('utf-8', errors='ignore')
    show = ignore_somecode(show)
    return show

re_comment_repoview_show_output = re.compile('^[\+-](begin_comment|comment|end_comment).*$')

def replace_comment_viewrepo_show_output(text):
    if len(text) > 0 and text[-1] != '\n':
        text = text + '\n'  # When'\ No newline at end of file', the line number is decreased. Hence, we add one newline

    new_text = ""
    for line in text.splitlines():
        new_text += re_comment_repoview_show_output.sub("", line)
        new_text += "\n"
    return new_text


def get_date(dirname, commit_hash):
    date = subprocess.check_output(
            ['git', '-C', '{}'.format(dirname), 'show', '{0}'.format(commit_hash), '-s', '--format=%ai'],
            universal_newlines=True
            )
    return date.splitlines()[0]

"""
Get an author of a commit.
Input:
dirname: The directory of the repository
commit_hash: SHA1 hash of the commit
"""
def get_author(dirname, commit_hash):
    try:
        author = subprocess.check_output(
                ['git', '-C', '{}'.format(dirname), 'show', '{0}'.format(commit_hash), '-s', '--format=%an'],
                universal_newlines=True
                )
    except UnicodeDecodeError:
        author = subprocess.check_output(
                ['git', '-C', '{}'.format(dirname), 'show', '{0}'.format(commit_hash), '-s', '--format=%an'],
                )
        try:
            author = author.decode('utf-8') 
        except UnicodeDecodeError:
            f = open('tmp/UnicodeDecodeError_commit_hash.txt','a')
            f.write('{0}\n'.format(commit_hash))
            author = author.decode('utf-8','ignore') 
            #author = unicode(author, errors='ignore')
            f.close()

    return author.splitlines()[0]

def get_all_hash(repodir):
    hash_list = subprocess.check_output(
            ['git', '-C', '{}'.format(repodir), 'log', '--all', '--pretty=format:%H'],
            universal_newlines=True
            ).splitlines()
    return hash_list

def get_commit_message(repodir, commit_hash):
    commit_msg_list = subprocess.check_output(
            ['git', '-C', '{}'.format(repodir), 'log', '--format=%B',
            '-n', '1', commit_hash],
            universal_newlines=True,
            errors="replace"
            ).splitlines()

    return "\n".join(commit_msg_list)

