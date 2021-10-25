import argparse
import os
import re
import sys
import collections
import subprocess
import pickle
import sqlite3
from revlink import diff_reader

from revlink import util
from revlink import blame
from revlink import git_reader

re_blank = re.compile('^\s*$')


"""
Remove empty lines.
"""
def remove_commentline(lines, linenums):
    for i, line in enumerate(lines):  # lines[0] has dummy
        if re_blank.match(line) and i in linenums:  # If the line is empty and matched with diff line
            linenums.remove(i)  # Remove the line


"""
Remove comment lines and empty lines
in order to make a dictionary.
In this dictionary, we will only see
lines correlated with source code.
"""
def ignore_comment_newline(diffmetrics_dict, repo_dir):
    data_dict = {}
    num_commit = len(diffmetrics_dict.keys())
    no_file_exit = r"^0*$"

    for counter, commithash in enumerate(diffmetrics_dict.keys()):
        print('{}/{} commits ...'.format(counter + 1, num_commit), end='\r')
        data_dict[commithash] = []

        """
        Consecutively analyze each of files in a commit.
        """
        for m_dict in diffmetrics_dict[commithash]:

            delete_FLAG = 0
            """
            If the analyzed file is newly added, the file does not have previous version,
            we do not analyze the file.
            """
            #if m_dict['prev'] == '0000000' or m_dict['prev'] == '000000000' or m_dict['prev'] == '0000000000':
            if re.match(no_file_exit, m_dict['prev']):  # We ignore the new added files.
                delete_FLAG = 1


            if delete_FLAG==0:
                linenums_del = set(m_dict['deleted'])

                source_code_pre = git_reader.git_show_module_without_comment(repo_dir, m_dict['prev'])


                lines_pre = source_code_pre.splitlines()  # all of the source code
                lines_pre.insert(0, '')  # text starts lines[1]

                """ Remove empty and comment lines in linenums_del"""
                remove_commentline(lines_pre, linenums_del)


                #print('Af')
                #print(linenums_del)

                """
                If we do not have any lines in linenums_del when we conducted the above procedures,
                we skip the file because this file does not have lines correlated defects.
                Otherwise, we update m_dict to remove useless lines (commnet lines).
                In addition, we make data_dict.
                """
                if len(linenums_del) == 0:
                    continue
                else:
                    m_dict['deleted'] = sorted(list(linenums_del))

                    data_dict[commithash].append(m_dict)



    return data_dict


"""
To identify defect inducing commits from defect fixing commits,
we use git blame.
In this function, we identify defect inducing commits and
return table_data.
table_data[commit_hash][file_name(present commit)][function_name(in defect inducing commit)]

This is because:
If we use the file name of the present commit and the present commit rename the file,
we cannot use git blame.
In addition, after this function, we extract the file name in defect inducing commit.
Hence, we use the file name of the present commit.

This function name will be used to identify which function induces defects.
Hence, we collect function names as well.
"""
def read_blame_data(data_dict, repo_dir):
    table_data = {}

    num_commit = len(data_dict.keys())
    for counter, commit_hash in enumerate(data_dict.keys()):

        print('{}/{} commits ...'.format(counter + 1, num_commit), end='\r')
        #print(commit_hash)
        #table_data[commit_hash] = []

        file_dict = {}
        for m_dict in data_dict[commit_hash]:

            file_name = m_dict['module_name_before'] # extract the file name of the previous commit

            """
            When a hunk has only comment lines, we get lines==[].
            Then, git blame outputs all of a file.

            Example:
            @@ -300,1 +300,1 @@ hogehoge_function:
            -  //sdfsdf
            +  //sdfsdf
            Then we got lines==[]. And therefore we got all of a file as an output of git blame.
            Hence, we skip the case.
            """
            if m_dict['deleted']!=[]:
                file_dict[file_name] = blame.git_blame(repo_dir, commit_hash, file_name, m_dict['deleted'])

        #print(commit_hash)
        #print(file_dict)
        table_data[commit_hash] = file_dict

    return table_data


"""
In this function, we extract all of information about defect inducing commits.
defectInducingCommitsDict is the return dictionary.
Which has [commit_hash][data (e.g., lines, author)][defect_inducing_commit_hash][defect inducing file][defect inducing line]
"""
def read_meta_info_defectInducingCommits(data_dict, repo_dir):


    re_meta_data = re.compile('([\^\w\d]+)\s+(|[\w/\.\$\+-]+\s+)(\d+)\s\((.*)\s(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2})\s([\+-]\d{4})\s+(\d+)\).*')
    SHA1_head_checker = re.compile('^\^')

    """
    This dictionary has data about defect inducing commits.
    All of data are about defect inducing commits (e.g., the numbers of lines are in defect inducing commits
    not fixing commits).
    """
    defectInducingCommitsDict = {}

    for commit_hash in data_dict.keys():
        defectInducingCommitsDict[commit_hash] = {'defectInducingLines': {}, 'defectInducingCommits': set(), 'author': {}, 'day': {}, 'time': {}, 'zone': {}}

        for file_name in data_dict[commit_hash].keys():

            """
            "line" has an one line output of git blame. We convert the output into
            important information using the regular expression of "re_meta_data"
            and store them into the dictionary.
            """
            for line in data_dict[commit_hash][file_name].splitlines():
                #print('Fix')
                #print(line)
                #print(commit_hash)
                #print(dateFixCommit.split(' '))
                #print(authorFixCommit)
                #print('Defect')
                #print(line)
                defectCommit_hash = re_meta_data.match(line).group(1) #SHA1

                if SHA1_head_checker.search(defectCommit_hash):
                    defectCommit_hash = defectCommit_hash[1:]

                if not defectCommit_hash in defectInducingCommitsDict[commit_hash]['defectInducingLines']:
                    defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash] = {}
                    defectInducingCommitsDict[commit_hash]['author'][defectCommit_hash] = {}
                    defectInducingCommitsDict[commit_hash]['day'][defectCommit_hash] = {}
                    defectInducingCommitsDict[commit_hash]['time'][defectCommit_hash] = {}
                    defectInducingCommitsDict[commit_hash]['zone'][defectCommit_hash] = {}

                #print(defectCommit_hash)
                defectInducingCommitsDict[commit_hash]['defectInducingCommits'].add(defectCommit_hash)
                defectInducingFile = re_meta_data.match(line).group(2).rstrip() # file name of the defect inducing commit
                if defectInducingFile == '':
                    defectInducingFile = file_name
                #print(re_meta_data.match(line).group(3)) #line number of the defect inducing commit
                defectInducingLine = re_meta_data.match(line).group(3)
                if not defectInducingFile in defectInducingCommitsDict[commit_hash]['author'][defectCommit_hash]:
                    defectInducingCommitsDict[commit_hash]['author'][defectCommit_hash][defectInducingFile] = {}
                    defectInducingCommitsDict[commit_hash]['author'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(4) #author
                    defectInducingCommitsDict[commit_hash]['day'][defectCommit_hash][defectInducingFile] = {}
                    defectInducingCommitsDict[commit_hash]['day'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(5) #defect inducing day
                    defectInducingCommitsDict[commit_hash]['time'][defectCommit_hash][defectInducingFile] = {}
                    defectInducingCommitsDict[commit_hash]['time'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(6) #defect inducing time
                    defectInducingCommitsDict[commit_hash]['zone'][defectCommit_hash][defectInducingFile] = {}
                    defectInducingCommitsDict[commit_hash]['zone'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(7) #defect inducing zone

                defectInducingCommitsDict[commit_hash]['author'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(4) #author
                defectInducingCommitsDict[commit_hash]['day'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(5) #defect inducing day
                defectInducingCommitsDict[commit_hash]['time'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(6) #defect inducing time
                defectInducingCommitsDict[commit_hash]['zone'][defectCommit_hash][defectInducingFile][defectInducingLine] = re_meta_data.match(line).group(7) #defect inducing zone
                
                #print(re_meta_data.match(line).group(8)) # line number of the defect fixing commit

                if not defectInducingFile in defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash]:
                    defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash][defectInducingFile] = []

                defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash][defectInducingFile].append(re_meta_data.match(line).group(3))
                #print(data_dict[commit_hash][file_name])
                #for line in data_dict[commit_hash][file_name]:

                #print(line)

        #"""
        #Before this line, we only see the outputs of git show (the present commit) and git blame.
        #However, we want to use names of function or something in defect inducing commits.
        #Hence, after this line, we get the output of git show using the defect inducing commits
        #and analyze them.
        #"""
        ##print(defectInducingCommitsDict[commit_hash]['defectInducingCommits'])
        ##print('git show of defect indusing commits')
        #for defectCommit_hash in defectInducingCommitsDict[commit_hash]['defectInducingCommits']:
        #    
        #    #if commit_hash=='2646080e3dc1a1da5be2c066329eb80e1ca0ef7b' or commit_hash=='f012a857f5e9b3bdd11a64dd0c16b4c805076594' or commit_hash=='b175cb755bd2b62a19dbf27daf07ae5354f9a079':
        #    #if commit_hash=='fa8dd785a2d82e190ada724aa1c46dbd66fb3067':
        #    #if commit_hash=='d1b70ffa03863b810813dd9d098b38500d4be424':

        #    #print(defectInducingCommitsDict[commit_hash]['defectInducingLines'])
        #    diffmetrics = diff_reader.collect_diffcode_metrics(
        #            defectCommit_hash, repo_dir 
        #            )

        #    keys = defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash].keys()

        #    #print(keys)
        #    for file_data in diffmetrics:

        #        if not file_data['module_name'] in keys: # ignore not correlated files
        #            continue

        #        """
        #        We use line numbers to extract information from the output of git show (in defect inducing commit).
        #        The line numbers also are in defect inducing commits.
        #        """
        #        for line in defectInducingCommitsDict[commit_hash]['defectInducingLines'][defectCommit_hash][file_data['module_name']]:

        #            for function_name in file_data['added_nums_with_functionName'].keys():

        #                if int(line) in file_data['added_nums_with_functionName'][function_name]:

        #                    if not defectCommit_hash in defectInducingCommitsDict[commit_hash]['defectInducingFunction']:
        #                        defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash] = {}

        #                    if not file_data['module_name'] in defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash]:
        #                        defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash][file_data['module_name']] = {}

        #                    if not function_name in defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash][file_data['module_name']]:
        #                        defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash][file_data['module_name']][function_name] = []


        #                    defectInducingCommitsDict[commit_hash]['defectInducingFunction'][defectCommit_hash][file_data['module_name']][function_name].append(line)


    return defectInducingCommitsDict


"""
Make defectFixingCommitsDict. This dictionary has
information about defect fixing commits.
"""
def read_meta_info_defectFixingCommits(data_dict, repo_dir, diffmetrics_dict, defectInducingCommitsDict):

    defectFixingCommitsDict = {}

    for commit_hash in data_dict.keys():

        dateFixCommit = re.split("\s", git_reader.get_date(repo_dir, commit_hash))
        authorFixCommit = git_reader.get_author(repo_dir, commit_hash)

        defectFixingCommitsDict[commit_hash] = {}
        defectFixingCommitsDict[commit_hash]['day'] = dateFixCommit[0]
        defectFixingCommitsDict[commit_hash]['time'] = dateFixCommit[1]
        defectFixingCommitsDict[commit_hash]['zone'] = dateFixCommit[2]
        defectFixingCommitsDict[commit_hash]['author'] = authorFixCommit


    return defectFixingCommitsDict

"""
Make the table "defect_fixing_commits"
"""
def make_defectFixingTable(db_name, defectFixingCommitsDict, cregit_hash_list):

    try:
        os.remove(db_name)
    except FileNotFoundError:
        pass

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    #cur.execute("CREATE TABLE defect_fixing_commits(commit_hash TEXT PRIMARY KEY, day TEXT, time TEXT, zone TEXT, author TEXT);")
    cur.execute("CREATE TABLE defect_fixing_commits(commit_hash TEXT PRIMARY KEY, day TEXT, time TEXT, zone TEXT);")
    for commit_hash in cregit_hash_list:
        #cur.execute('INSERT INTO defect_fixing_commits(commit_hash, day, time, zone, author) VALUES(?,?,?,?,?)',(commit_hash, defectFixingCommitsDict[commit_hash]['day'], defectFixingCommitsDict[commit_hash]['time'], defectFixingCommitsDict[commit_hash]['zone'], defectFixingCommitsDict[commit_hash]['author']))
        cur.execute('INSERT INTO defect_fixing_commits(commit_hash, day, time, zone) VALUES(?,?,?,?)',(commit_hash, defectFixingCommitsDict[commit_hash]['day'], defectFixingCommitsDict[commit_hash]['time'], defectFixingCommitsDict[commit_hash]['zone']))
    conn.commit()
    conn.close()

"""
Make the table "defect_inducing_lines"
"""
def make_defectInducingTable(db_name, defectInducingCommitsDict, cregit_hash_list):

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    #cur.execute("""CREATE TABLE defect_inducing_lines(commit_hash TEXT,
    #        file_name TEXT, function_name TEXT, line INTEGER, day TEXT, time TEXT, zone TEXT, author TEXT, fixing_commit_hash TEXT,
    #        PRIMARY KEY (commit_hash, file_name, function_name, line, fixing_commit_hash));""")
    cur.execute("""CREATE TABLE defect_inducing_lines(commit_hash TEXT,
            file_name TEXT, line INTEGER, day TEXT, time TEXT, zone TEXT, fixing_commit_hash TEXT,
            PRIMARY KEY (commit_hash, file_name, line, fixing_commit_hash));""")


    for commit_hash in cregit_hash_list:

        data_dict = defectInducingCommitsDict[commit_hash]
        
        for defective_commit_hash in data_dict['defectInducingCommits']:

            for file_name in data_dict['defectInducingLines'][defective_commit_hash].keys():

                previous_execution = ''
                for line in list(map(str,sorted(list(map(int,data_dict['defectInducingLines'][defective_commit_hash][file_name]))))):

                    #cur.execute("""INSERT INTO defect_inducing_lines(commit_hash, file_name, function_name, line, day, time, zone, author, fixing_commit_hash)
                    #        VALUES("{0}","{1}",'{2}',{3},"{4}","{5}","{6}","{7}","{8}")""".format(defective_commit_hash, file_name, function_name.replace("'",'"'), int(line),
                    #            data_dict['day'][defective_commit_hash][file_name][line], data_dict['time'][defective_commit_hash][file_name][line],
                    #            data_dict['zone'][defective_commit_hash][file_name][line], data_dict['author'][defective_commit_hash][file_name][line],
                    #            commit_hash))
                    #present_execution = """INSERT INTO defect_inducing_lines(commit_hash, file_name, function_name, line, day, time, zone, author, fixing_commit_hash)
                    present_execution = """INSERT INTO defect_inducing_lines(commit_hash, file_name, line, day, time, zone, fixing_commit_hash)
                            VALUES("{0}","{1}",{2},"{3}","{4}","{5}","{6}")""".format(defective_commit_hash, file_name, line,
                                data_dict['day'][defective_commit_hash][file_name][line], data_dict['time'][defective_commit_hash][file_name][line],
                                data_dict['zone'][defective_commit_hash][file_name][line],commit_hash)

                    """
                    Sometimes, developers copy their source code ant past it into the same file (or make new files).
                    If the source code has defect, developers need to fix all of them (original location and pasted location).
                    In this case, our scripts identify the same line (,which induces defect) repeated. Hence, data_dict['defectInducingFunction'][defective_commit_hash][file_name]
                    has two same lines (for example, "1f46b991da9b91585608a0babd3eda39485dce09" is a defect fixing commit. This commit has two files
                    that are "hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/java/org/apache/hadoop/mapreduce/util/ResourceCalculatorPlugin.java"
                    and "hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-common/src/main/java/org/apache/hadoop/yarn/util/ResourceCalculatorPlugin.java".
                    These two clone files are originaly exists as a file in "a196766ea07775f18ded69bd9e8d239f8cfd3ccc" as "mapreduce/src/java/org/apache/hadoop/mapreduce/util/ResourceCalculatorPlugin.java".)
                    Hence, if we remove this if statement, we would get sqlite3.IntegrityError: UNIQUE constraint failed.
                    """
                    if previous_execution != present_execution:
                        cur.execute("""INSERT INTO defect_inducing_lines(commit_hash, file_name, line, day, time, zone, fixing_commit_hash)
                                VALUES(?,?,?,?,?,?,?)""",(defective_commit_hash, file_name, line,
                                    data_dict['day'][defective_commit_hash][file_name][line], data_dict['time'][defective_commit_hash][file_name][line],
                                    data_dict['zone'][defective_commit_hash][file_name][line], commit_hash))

                    previous_execution = present_execution
    conn.commit()
    conn.close()


"""
Make the table "defect_inducing_commits"
"""
def make_defectInducingCommitsTable(db_name, defectInducingCommitsDict, cregit_hash_list, all_cregit_hash_list):

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE defect_inducing_commits(commit_hash TEXT PRIMARY KEY, defect INTEGER);""")


    defective_commit_hash = set()
    for commit_hash in cregit_hash_list:

        defective_commit_hash = defective_commit_hash | defectInducingCommitsDict[commit_hash]['defectInducingCommits']
        
    for commit_hash in all_cregit_hash_list:

        if commit_hash in defective_commit_hash:
            #cur.execute("""INSERT INTO defect_inducing_commits(commit_hash, defect)
            #        VALUES('{0}',1)""".format(commit_hash))
            cur.execute("""INSERT INTO defect_inducing_commits(commit_hash, defect)
                    VALUES(?,?)""",(commit_hash,1))
        else:
            #cur.execute("""INSERT INTO defect_inducing_commits(commit_hash, defect)
            #        VALUES('{0}',0)""".format(commit_hash))
            cur.execute("""INSERT INTO defect_inducing_commits(commit_hash, defect)
                    VALUES(?,?)""",(commit_hash,0))

    conn.commit()
    conn.close()


def make_cregit2orgCommitHashTable(db_name, p_name):

    cregit2org_dict = util.load_pickle("./data/{0}_cregit2org_hash_dict.pickle".format(p_name))

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE cregit2org_commit_hashes(cregit_commit_hash TEXT PRIMARY KEY, org_commit_hash TEXT);""")

    for cregit_hash in cregit2org_dict.keys():
        cur.execute("""INSERT INTO cregit2org_commit_hashes(cregit_commit_hash, org_commit_hash)
                VALUES(?,?)""",(cregit_hash, cregit2org_dict[cregit_hash]))

    conn.commit()
    conn.close()


def main(p_name, repo_dir, pickle_path, db_path):

    """
    TUTORIAL and TEST
    """
    #cregit_hash_list = ['2646080e3dc1a1da5be2c066329eb80e1ca0ef7b','f012a857f5e9b3bdd11a64dd0c16b4c805076594','b175cb755bd2b62a19dbf27daf07ae5354f9a079']
    #all_cregit_hash_list = ['c555400ca134991e39d5e3a565fcd2215abe56f6','9b0369c773c1d350a05435d8d3ec4e954828fb82','2646080e3dc1a1da5be2c066329eb80e1ca0ef7b','f012a857f5e9b3bdd11a64dd0c16b4c805076594','b175cb755bd2b62a19dbf27daf07ae5354f9a079','40b556d3742a1f65d67e2d4c760d0b13fe8be5b7','ffe8b77a617efd802a9d4ba7e42b163fbd9a250b']

    #print(db_path)
    #if not (os.path.exists(pickle_path) and os.path.exists(db_path)):
    #    exit('file not found.')

    diffmetrics_dict = util.load_pickle(pickle_path)

    all_cregit_hash_list = util.load_pickle('./data/{0}_cregit_commit_hash.pickle'.format(p_name))
    cregit_hash_list = diffmetrics_dict.keys()

    print("# of all cregit commits: {0}".format(len(all_cregit_hash_list)))
    print("# of all defect fixing commits: {0}".format(len(cregit_hash_list)))

    print('### Step 1: Ignore comment and newlines.')
    data_dict = ignore_comment_newline(diffmetrics_dict, repo_dir)
    util.dump_pickle("./data/{0}_make_db_step1.pickle".format(p_name), data_dict)
    #print("CAUTION: MIGHT USE OLD DATA")
    data_dict = util.load_pickle("./data/{0}_make_db_step1.pickle".format(p_name))

    print('### Step 2: Read all data from the git repository.')
    data_dict = read_blame_data(data_dict, repo_dir)
    util.dump_pickle("./data/{0}_make_db_step2.pickle".format(p_name), data_dict)
    #print("CAUTION: MIGHT USE OLD DATA")
    data_dict = util.load_pickle("./data/{0}_make_db_step2.pickle".format(p_name))


    print('### Step 3: Read meta information from the data_dict.')
    defectInducingCommitsDict = read_meta_info_defectInducingCommits(data_dict, repo_dir)
    defectFixingCommitsDict = read_meta_info_defectFixingCommits(data_dict, repo_dir, diffmetrics_dict, defectInducingCommitsDict)

    #print(defectInducingCommitsDict['2646080e3dc1a1da5be2c066329eb80e1ca0ef7b'])
    #print(diffmetrics_dict)
    #print('')

    #print(table_dict)

    print('### Step 4: Make database.')

    make_defectFixingTable(db_path, defectFixingCommitsDict, cregit_hash_list)
    make_defectInducingTable(db_path, defectInducingCommitsDict, cregit_hash_list)
    make_defectInducingCommitsTable(db_path, defectInducingCommitsDict, cregit_hash_list, all_cregit_hash_list)
    make_cregit2orgCommitHashTable(db_path, p_name)
    #print(data_dict)
    #print(data_dict['f012a857f5e9b3bdd11a64dd0c16b4c805076594']['src/rest.cpp']['static bool rest_getutxos(HTTPRequest* req, const std::string& strURIPart)'])
