import os
import oss2
import pymongo
import chamo_common.config
from chamo_common.config import get_oss_mongo
task_table_name=chamo_common.config.task_table_name
bucket, mydb = get_oss_mongo()
task_table=mydb[task_table_name]

# task_table.insert_one({"task":"init", "status":2, "name":"swiss_bern"})
task_table.update_one({"name":"colorado_ski"},{"$set":{"edit_mode":"edit"}})
for x in task_table.find({}):
    print(x)