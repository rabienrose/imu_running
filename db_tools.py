import os
import oss2
import pymongo
import chamo_common.config
from chamo_common.config import get_oss_mongo
task_table_name=chamo_common.config.task_table_name
bucket, mydb = get_oss_mongo()
task_table=mydb[task_table_name]

# task_table.delete_one({"name":"chamo"})
task_table.update_many({"status":{"$exists":False}},{"$set":{"status":2,"task":""}})
for x in task_table.find({}):
    print(x)