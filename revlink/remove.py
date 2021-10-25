import argparse
import os
import pickle
import re
import sys

from revlink import diff_reader

from revlink import util

class Remove:
    def __init__(self, repo_dir, read_diff_result_path):
        self.repo_dir = repo_dir
        self.pickle_path = read_diff_result_path

    def main(self):

        if not os.path.exists(self.pickle_path):
            exit('file not found.')

        diffmetrics_dict = util.load_pickle(self.pickle_path)
        num_commit = len(diffmetrics_dict.keys())
        print("Data file is loaded.\n # of commit: {0}".format(num_commit))


        """
        Remove "files" which are not correlated to source code executions.
        A commit can include several files, and therefore, we remove
        such files.
        We identify such files using the following criteria:
          - Do not add source code
          - Only fix newlines
          - Both addition and deletinon are not correlated to source code (e.g., comment lines).

        Finally, we remove such files and make a new dictionary.
        """

        no_file_exit = r"^0*$"
        for counter, commit_hash in enumerate(diffmetrics_dict.keys()):
        #for counter, commit_hash in enumerate(['6eb00e6b1b0cf758841cd69bb424513c86377c23', '702200014df99e32658941e2352049727ef34c88']):
            print('{}/{} commits ...'.format(counter + 1, num_commit), end='\r')
            module_datalist = diffmetrics_dict[commit_hash]
            num_module = len(module_datalist)
            delete_index = []
            for i in range(0, num_module):
                m_dict = module_datalist[i]
                added = m_dict['added']
                deleted = m_dict['deleted']
                prev_hash = m_dict['prev']
                curr_hash = m_dict['curr']
                if re.match(no_file_exit, prev_hash):  # We ignore the new added files.
                    if not diff_reader.isMeaningfulChange(self.repo_dir, curr_hash, added):
                        # Remove files do not add source code
                        delete_index.append(i)
                    continue

                if not diff_reader.isChanged(self.repo_dir, prev_hash, curr_hash):
                    # Remove files only fix newlines
                    delete_index.append(i)
                    continue
                prev_flag = diff_reader.isMeaningfulChange(self.repo_dir, prev_hash, deleted)
                curr_flag = diff_reader.isMeaningfulChange(self.repo_dir, curr_hash, added)
                if not prev_flag and not curr_flag:  # Remove files are not correlated with source code.
                    delete_index.append(i)
            if len(delete_index):
                print(commit_hash, len(delete_index), 'module deleted.')
            for num, i in enumerate(delete_index):  # When we remove list, we need to remove index as well.
                # print(diffmetrics_dict[commit_hash][i - num]['module_name'])
                del diffmetrics_dict[commit_hash][i - num]

        output_name = re.sub('\.[\w]+$', '-removed.pickle', self.pickle_path)
        print('save to {}.'.format(output_name))
        #print(diffmetrics_dict)
        util.dump_pickle(output_name, diffmetrics_dict)

