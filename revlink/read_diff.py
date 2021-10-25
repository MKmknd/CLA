#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import collections
import csv
import pickle
import sys

import re

from revlink import diff_reader

from revlink.git_reader import get_all_hash
from revlink.git_reader import get_commit_message

from revlink import util


class ReadDiff:
    def __init__(self, p_name=None, repo_dir=None, pickle_dest=None, key_issue2hash_dict_pickle_path=None, target_issue2hash_dict_pickle_path_list=[], target_ILA_num_list=[]):

        self.p_name = p_name
        self.repo_dir = repo_dir
        self.pickle_dest = pickle_dest
        self.key_issue2hash_dict_pickle_path = key_issue2hash_dict_pickle_path
        self.target_issue2hash_dict_pickle_path_list = target_issue2hash_dict_pickle_path_list
        self.target_ILA_num_list = target_ILA_num_list

    def combine_commit_set(self, pickle_path):
        issue2hash_dict = util.load_pickle(pickle_path)
        for issue_id in issue2hash_dict.keys():
            self.defect_fixing_commit_set = self.defect_fixing_commit_set | set(issue2hash_dict[issue_id])

    def combine_issue2hash_dict(self):

        self.defect_fixing_commit_set = set()

        self.combine_commit_set(self.key_issue2hash_dict_pickle_path)

        for pickle_path in self.target_issue2hash_dict_pickle_path_list:
            self.combine_commit_set(pickle_path)


    def read_cregit_commit_hash(self, hash_list):

        re_former_commit_id = r"\nFormer-commit-id: ([0-9a-f]+)$"

        org2cregit_hash_dict = {}
        cregit2org_hash_dict = {}
        re_former_commit_id_error = set()
        for idx, commit_hash in enumerate(hash_list):

            if idx%100==0:
                print("run: {0}/{1}".format(idx, len(hash_list)))
            log = get_commit_message(self.repo_dir, commit_hash)

            match = re.search(re_former_commit_id, log)
            if not match:
                print("re former commit id error")
                print(commit_hash)
                print(log)
                re_former_commit_id_error.add(commit_hash)
                continue
            org2cregit_hash_dict[match.group(1)] = commit_hash
            cregit2org_hash_dict[commit_hash] = match.group(1)

        util.dump_pickle("./data/{0}_re_former_commit_id_error_{1}.pickle".format(self.p_name, ",".join(self.target_ILA_num_list)), re_former_commit_id_error)

        return org2cregit_hash_dict, cregit2org_hash_dict

    def main(self):
        """
        Extract the all hashs
        """
        print('### Step 1: Read commit hash')
        # remove the latest commit (I added this commit) and the first commit (since
        # such a commit does not have the original commit id)
        # hash_list includes cregit hashes
        hash_list = get_all_hash(self.repo_dir)[1:-1]
        print('# of hash:', len(hash_list))

        # self.defect_fixing_commit_set that is 
        # created by self.combine_issue2hash_dict() includes original hashes
        self.combine_issue2hash_dict()

        num_commit = len(self.defect_fixing_commit_set)
        print("# of defect fixing commit candidates: {0:,}".format(num_commit))


        print('### Step 2: Corresponding cregit commit hash and original commit hash.')
        org2cregit_hash_dict, cregit2org_hash_dict = self.read_cregit_commit_hash(hash_list)
        util.dump_pickle('data/{0}_org2cregit_hash_dict.pickle'.format(self.p_name), org2cregit_hash_dict)
        util.dump_pickle('data/{0}_cregit2org_hash_dict.pickle'.format(self.p_name), cregit2org_hash_dict)
        org2cregit_hash_dict = util.load_pickle('data/{0}_org2cregit_hash_dict.pickle'.format(self.p_name))

        print('### Step 3: Find diff lines.')
        diffmetrics_dict = collections.OrderedDict()

        for counter, org_commit_hash in enumerate(self.defect_fixing_commit_set):

            if not org_commit_hash in org2cregit_hash_dict:
                continue

            cregit_commit_hash = org2cregit_hash_dict[org_commit_hash]

            """
            If log messages include at least one issue id which corresponds to
            a Bug issue report, we proecss such commits
            """
            print('{}/{} commits ...'.format(counter + 1, num_commit), end='\r')
            diffmetrics_dict[cregit_commit_hash] = diff_reader.collect_diffcode_metrics(
                    cregit_commit_hash, self.repo_dir 
                    )

        print('save data to {}'.format(self.pickle_dest))
        util.dump_pickle(self.pickle_dest, diffmetrics_dict)
        util.dump_pickle('data/{0}_cregit_commit_hash.pickle'.format(self.p_name), hash_list)
        print(len(diffmetrics_dict.keys()), 'commits in pickle object')



