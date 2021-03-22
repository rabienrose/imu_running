import os
import oss2
import pymongo


tile_size=256
path_img_zoom=16
video_seg_length=15
target_fps=25

task_table_name="task"
oss_root="phone_sport"
patch_path="patches"

use_internal=True
if use_internal:
    url="mongodb://root:La_009296@dds-2ze0c5fb5b9bf554118470.mongodb.rds.aliyuncs.com:3717/admin"
    endpoint = os.getenv('OSS_TEST_ENDPOINT', 'https://oss-cn-beijing-internal.aliyuncs.com') # internal net
else:
    url="mongodb://root:La_009296@dds-2ze0c5fb5b9bf554-pub.mongodb.rds.aliyuncs.com:3717/admin"
    endpoint = os.getenv('OSS_TEST_ENDPOINT', 'https://oss-accelerate.aliyuncs.com') # external net
access_key_id = os.getenv('OSS_TEST_ACCESS_KEY_ID', 'LTAI4GJDtEd1QXeUPZrNA4Yc')
access_key_secret = os.getenv('OSS_TEST_ACCESS_KEY_SECRET', 'rxWAZnXNhiZ8nemuvshvKxceYmUCzP')
bucket_name='ride-v'

def get_oss_mongo():
    bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)
    myclient = pymongo.MongoClient(url)
    mydb=myclient["imu_run"]
    return bucket, mydb

def get_config():
    bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)
    myclient = pymongo.MongoClient(url)
    return [bucket, myclient]

def drop_db(db_name):
    myclient = pymongo.MongoClient(url)
    myclient.drop_database(db_name)

def list_db():
    myclient = pymongo.MongoClient(url)
    for db in myclient.list_databases():
        print(db)