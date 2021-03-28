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
from chamo_common.util import verify_kml
from flask_httpauth import HTTPBasicAuth
from flask import jsonify, abort, make_response
app = Flask(__name__)
auth = HTTPBasicAuth()
bucket, mydb = get_oss_mongo()
task_table_name=chamo_common.config.task_table_name
oss_root=chamo_common.config.oss_root
patch_path=chamo_common.config.patch_path
account_table = mydb["account"]

@auth.get_password
def get_password(username):
    password=""
    for x in account_table.find({"name":username},{"_id":0,"password":1}):
        password=x["password"]
    if password=="":
        return None
    return password

@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'error': 'invalid_access' } ), 401)

@app.route('/user_info', methods = ['POST'])
@auth.login_required
def user_info():
    account=auth.username()
    re=list(account_table.find({"name":account},{"_id":0,"password":0})) 
    if len(re)==0:
        return json.dumps(["account_not_exist"])
    user_info=re[0]
    user_info_return={}
    user_info_return["name"]=user_info["name"]
    user_tasks=[]
    for x in mydb[task_table_name].find({"owner":user_info["name"]},{"_id":0,"name":1, "task":1, "edit_mode":1, "edit_time":1}):
        info={}
        info["name"]=x["name"]
        info["has_kml"]=False
        if bucket.object_exists("phone_sport/ws/"+x["name"]+"/chamo.kml"):
            info["has_kml"]=True
        info["edit_time"]=x["edit_time"]
        info["edit_mode"]=""
        if "edit_mode" in x:
            info["edit_mode"]=x["edit_mode"]
        user_tasks.append(info)
    user_info_return["user_tasks"]=user_tasks
    return json.dumps(user_info_return)

@app.route('/login_create', methods=['POST'])
def regist():
    regist_data = request.form['regist_data']
    regist_obj = json.loads(regist_data)
    account=regist_obj["account"]
    password=regist_obj["password"]
    if len(account)>=1 and len(account)<20 and len(password)>=1 and len(password)<20:
        find_one=False
        for _ in account_table.find({"name":account},{"_id":0,"password":1}):
            find_one=True
        if find_one==False:
            account_table.insert({"name":account, "password":password})
            return json.dumps(["regist_ok"])
        else:
            if password==password:
                return json.dumps(["login_ok"])
            else:
                return json.dumps(["password_wrong"])
    else:
        return json.dumps(["account_or_password_len_invalid"])

@app.route('/verify_proj', methods=['GET'])
def verify_proj():
    proj_name = request.values.get('proj_name')
    result = request.values.get('result')
    print(proj_name, result)
    if result=="ok":
        mydb[task_table_name].update_one({"name":proj_name},{"$set":{"edit_mode":"done"}})
    else:
        mydb[task_table_name].update_one({"name":proj_name},{"$set":{"edit_mode":"re-edit"}})
    return json.dumps(["ok"])

@app.route('/get_proj_list', methods=['GET'])
def get_proj_list():
    mode = request.values.get('mode')
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
            info["task"]=""
            info["status"]=""
            info["edit_time"]=""
            info["owner"]=""
            info["edit_mode"]=""
            info["info"]=""
            for x in mydb[task_table_name].find({"name":proj_name},{"_id":0,"task":1, "status":1, "info":1, "owner":1, "edit_time":1,"edit_mode":1}):
                info["task"]=x["task"]
                info["status"]=x["status"]
                if "info" in x:
                    info["info"]=x["info"]
                else:
                    info["info"]=""
                if "owner" in x:
                    info["owner"]=x["owner"]
                else:
                    info["owner"]=""
                if "edit_mode" in x:
                    info["edit_mode"]=x["edit_mode"]
                else:
                    info["edit_mode"]=""
                if "edit_time" in x:
                    info["edit_time"]=str(x["edit_time"])
                else:
                    info["edit_time"]=""
            if mode=="no_user":
                if info["owner"]!="":
                    continue
            elif mode=="pending":
                if info["edit_mode"]== "pending" and info["task"]=="proc" and info["status"]==2:
                    pass
                else:
                    continue
            re_list.append(info)
    return json.dumps(re_list)

@app.route('/modify_status', methods=['GET'])
def modify_status():
    traj = request.values.get('traj')
    task = request.values.get('task')
    status = int(request.values.get('status'))
    owner = request.values.get('owner')
    edit_mode = request.values.get('edit_mode')
    if task!="":
        mydb[task_table_name].update_one({"name":traj},{"$set":{"status":status, "task":task}})
    elif owner!="":
        mydb[task_table_name].update_one({"name":traj},{"$set":{"owner":owner}})
    elif edit_mode!="":
        mydb[task_table_name].update_one({"name":traj},{"$set":{"edit_mode":edit_mode}})
    return json.dumps(["ok"])

@app.route('/choose_task', methods=['GET'])
@auth.login_required
def choose_task():
    proj = request.values.get('proj')
    account=auth.username()
    t = time.localtime()
    current_time = time.strftime("%y%m%d", t)
    int_data=int(current_time)
    print({"proj":proj,"edit_mode":"edit","owner":account,"edit_time":int_data})
    mydb[task_table_name].update_one({"name":proj},{"$set":{"edit_mode":"edit","owner":account,"edit_time":int_data,"task":"","status":2}},True)
    return json.dumps(["ok"])

@app.route('/send_kml', methods=['POST'])
@auth.login_required
def send_kml():
    proj = request.form['proj']
    str_kml = request.form['str_kml']
    f = open("chamo.kml","w")
    f.write(str_kml)
    f.close()
    [re,info] = verify_kml(".")
    if re==False:
        return json.dumps([info])
    mydb[task_table_name].update_one({"name":proj},{"$set":{"edit_mode":"pending"}})
    oss_path=oss_root+"/ws/"+proj+"/chamo.kml"
    bucket.put_object_from_file(oss_path, "chamo.kml")
    return json.dumps(["ok"])

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
