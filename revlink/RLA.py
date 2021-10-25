import argparse
import sys
from revlink import read_diff
from revlink import remove
from revlink import make_db

# revision linking algorithm
class RLA:
    def __init__(self, p_name, repo_dir, out_dir, issue2hash_dict_BASE_DIR, db_path, target_ILA_num_list=None, blind_rate=50):
        self.p_name = p_name # project name (repository name)
        self.repo_dir = repo_dir # path/to/cregit/repository
        self.out_dir = out_dir # please input an output directory
        self.issue2hash_dict_BASE_DIR = issue2hash_dict_BASE_DIR # path/to/directory/where/pickle/files/of/issue2hash/dict/exists

        # numbers of ILAs which are used with the keyword extraction. e.g., "3,5"
        if target_ILA_num_list==None:
            self.target_ILA_num_list = []
        else:
            self.target_ILA_num_list = target_ILA_num_list.split(",")

        # path to the output database including defect inducing commit info
        self.db_path = db_path


        self.TIME_FILTERING_MIN = 10
        self.NTEXT_TH = 3
        self.WORD_ASSOC_TH = 5
        self.COMMENT_COS_TH = 4
        self.NSD_SIM_COS_TH = 2
        self.blind_rate = blind_rate

        self.ILA_dict_update()

        self.cregit_repo = "{0}/{1}".format(self.repo_dir, self.p_name)
        self.output = "{0}/{1}_read_diff_out.pickle".format(self.out_dir, self.p_name)

    def ILA_dict_update(self):

        self.ILA_dict = {"1": "{0}_keyword_extraction_{1}_with_restriction".format(self.p_name, self.blind_rate),
                "all": "{0}_all_commits".format(self.p_name)}

        self.key_pic_path = "{0}/{1}.pickle".format(self.issue2hash_dict_BASE_DIR, self.ILA_dict["1"])

        self.target_pic_path_list = []
        for target_ILA_num in self.target_ILA_num_list:
            self.target_pic_path_list.append("{0}/{1}.pickle".format(
                    self.issue2hash_dict_BASE_DIR, self.ILA_dict[target_ILA_num]))


    def main(self):

        read_diff_obj = read_diff.ReadDiff(self.p_name, self.cregit_repo, self.output, self.key_pic_path, self.target_pic_path_list, self.target_ILA_num_list)
        read_diff_obj.main()

        remove_obj = remove.Remove(self.cregit_repo, self.output)
        remove_obj.main()

        self.output = "{0}/{1}_read_diff_out-removed.pickle".format(self.out_dir, self.p_name)
        make_db.main(self.p_name, self.cregit_repo, self.output, self.db_path)

