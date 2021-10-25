
## Abstract
Revision Linking Algorithm (RLA) is now available.
This package implements an RLA (a.k.a. CLA) to implement a SZZ algorithm.
We need to also use any issue linking algorithms (ILA) before
applying this package.


## How to install

```bash
$ pip3 instal -e .
```

If you use pipenv,

```bash
$ pipenv install git+https://github.com/MKmknd/revlink#egg=revlink
```

If you use pip,
```bash
$ pip install git+ssh://git@github.com/MKmknd/revlink.git
```


## How to use
The following is a very small example

```
from revlink import RLA
if __name__=="__main__":
    rla_obj = RLA.RLA("avro", "./repository_cregit", "./data", "./defectfixingcommit/data", "./db/avro_3_14.db", "3,14")
    rla_obj.main()
```

In this case, we would have:
- ./repository_cregit/: This directory includes a view repository (a repository that is processed by cregit)
- ./data: This directory: This directory will have temporary files
- ./defectfixingcommit/data: This directory has defect fixing commit dataset (pickle files: key: Bug issue report id, value: list of commit hashes)
- ./db: This directory will have the result (database called avro_3_13.db)


