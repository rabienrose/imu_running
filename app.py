import requests
import os
import pymongo
import oss2
import numpy as np
from chamo_common.config import get_oss_mongo
import random
import time
import json
import math
from datetime import datetime
from flask import Flask
from flask import render_template
from flask import request, redirect, url_for
from random import randint
import chamo_common.config
from flask import jsonify, abort, make_response
app = Flask(__name__)
bucket, mydb = get_oss_mongo()
task_table_name=chamo_common.config.task_table_name
oss_root=chamo_common.config.oss_root
patch_path=chamo_common.config.patch_path

@app.route('/get_proj_list', methods=['POST'])
def get_proj_list():
    re_list=[]
    oss_prefix=oss_root+"/ws"
    for obj in oss2.ObjectIterator(bucket, prefix=oss_prefix+"/", delimiter="/"):
        vec = obj.key.split("/")
        if len(vec)==4:
            proj_name=vec[2]
            info={}
            info["name"]=proj_name
            if not bucket.object_exists(obj.key+"chamo.mp4"):
                continue
            for x in mydb[task_table_name].find({"name":proj_name},{"_id":0,"task":1, "status":1, "info":1}):
                info["task"]=x["task"]
                info["status"]=x["status"]
                if "info" in x:
                    info["info"]=x["info"]
                else:
                    info["info"]=""
            re_list.append(info)
    return json.dumps(re_list)

@app.route('/reqeust_proc', methods=['POST'])
def reqeust_proc():
    proj_name = request.values.get('proj_name')
    mydb[task_table_name].update_one({"name":proj_name},{"$set":{"status":2, "task":"init"}},True)
    return json.dumps(["ok"])

if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'xxx'
    app.config['UPLOAD_FOLDER']='./raw'
    app.debug = True
    app.run('0.0.0.0', port=8000)
