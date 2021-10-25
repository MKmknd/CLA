import pickle
import sqlite3
import sys
import yaml
import json

def dump_pickle(f_name, data):

    with open(f_name, "wb") as f:
        pickle.dump(data, f)


def load_pickle(f_name):

    with open(f_name, "rb") as f:
        data = pickle.load(f)

    return data


def replace_cregit_hash_to_org(data_dict, hash_dict):

    return_dict = {}
    for commit_hash in data_dict.keys():
        return_dict[hash_dict[commit_hash]] = data_dict[commit_hash]

    return return_dict

def dump_corpus_line2line(f_name, corpus):
    with open(f_name, "w") as f:
        for row in corpus:
            if len(row)==0:
                continue
            elif row[-1]=="\n":
                f.write(row[:-1] + "\n")
            else:
                f.write(row + "\n")

def read_yaml(f_path):
    with open(f_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    return data

def read_json(f_path):
    with open(f_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def dump_json(f_path, data, indent=4):
    with open(f_path, 'w') as f:
        json.dump(data, f, indent=indent)

