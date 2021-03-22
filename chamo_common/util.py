import json
from pprint import pprint
import os
import os.path
from os import listdir
import shutil
from os.path import isfile, join
import pyproj
import math
import oss2
import struct
import numpy as np
import datetime
import logging
import unittest
from logging import handlers
import calendar
import time
import sys
import requests
import chamo_common.config
from lxml import etree
import subprocess
import re
import traceback

task_table_name=chamo_common.config.task_table_name
oss_root=chamo_common.config.oss_root
patch_path=chamo_common.config.patch_path
video_seg_length=chamo_common.config.video_seg_length
target_fps=chamo_common.config.target_fps
path_img_zoom=chamo_common.config.path_img_zoom
tile_size=chamo_common.config.tile_size


def get_2d_dist(v1, v2):
    return math.sqrt((v1[0]-v2[0])*(v1[0]-v2[0])+(v1[1]-v2[1])*(v1[1]-v2[1]))

def get_sec(time_str):
    v=time_str.split(":")
    if len(v)==3:
        sec=int(v[0])*3600+int(v[1])*60+int(v[2])
    else:
        sec=int(v[0])*60+int(v[1])
    return sec

def deg2wc(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x = (lon_deg+180.0)/360.0*n*tile_size
    y = (1.0 - math.asinh(math.tan(lat_rad))/math.pi)/2*n*tile_size
    return [int(x),int(y)]

def deg2tile(lat_deg, lon_deg, zoom):
    xy = deg2wc(lat_deg, lon_deg, zoom)
    return [int(xy[0]//tile_size), int(xy[1]//tile_size)]

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def get_bounding_box(path_info):
    xs=[]
    ys=[]
    for item in path_info:
        xs.append(item["p"][0])
        ys.append(item["p"][1])
    return [min(xs),max(xs),min(ys),max(ys)]

def inter_float(v1,v2,t1, t2, t):
    if t1==t2:
        return v1
    else:
        return (t-t1)/(t2-t1)*(v2-v1)+v1

def get_img_posi(t, path_seg_list):
    count=0
    for item in path_seg_list:
        t1=item["time"][0]
        t2=item["time"][1]
        if t>=t1 and t<=t2:
            p1=item["posi"][0]
            p2=item["posi"][1]
            if t1==t2:
                return None,-2
            x=inter_float(p1[0],p2[0],t1, t2, t)
            y=inter_float(p1[1],p2[1],t1, t2, t)
            return [int(x),int(y)],count
        count=count+1
    return None,-1

def verify_kml(tmp_local):
    try:
        f = open(tmp_local+"/chamo.kml","r")
        kml_obj = etree.parse(f)
        root=kml_obj.getroot()
        ns="{http://www.opengis.net/kml/2.2}"
        place_markers=root[0].findall(ns+"Placemark")
        last_s_time=0
        for mk in place_markers:
            name=mk.find(ns+"name").text
            if " " in name:
                vec=name.split(" ")
                name=vec[0]
            if ":" in name:
                two_v = name.split("-")
                if len(two_v)==1:
                    s_time=get_sec(two_v[0])
                    e_time=get_sec(two_v[0])
                else:
                    s_time=get_sec(two_v[0])
                    e_time=get_sec(two_v[1])
                if last_s_time>s_time:
                    return [False,"时间非递增，t1="+str(last_s_time)+" t2="+str(s_time)]
                last_s_time=s_time
    except:
        var = traceback.format_exc()
        return [False,"出错： "+var]
    return [True,"ok"]

def get_img_2_posi_list(img_count, tmp_local):
    node_2_path=[]
    path_posi=[]
    imgid_2_posi=[]
    s_path=[]
    cur_s=0
    s_path.append(0)
    f = open(tmp_local+"/chamo.kml","r")
    kml_obj = etree.parse(f)
    root=kml_obj.getroot()
    ns="{http://www.opengis.net/kml/2.2}"
    place_markers=root[0].findall(ns+"Placemark")
    last_posi=[]
    last_s_time=0
    path_meta=[]
    for mk in place_markers:
        coor_str = mk.find(ns+"Point").find(ns+"coordinates").text
        v_str=coor_str.split(",")
        wc2 = deg2wc(float(v_str[1]), float(v_str[0]), path_img_zoom)
        cur_posi=[wc2[0],wc2[1],float(v_str[2])]
        name=mk.find(ns+"name").text
        param=""
        if " " in name:
            vec=name.split(" ")
            name=vec[0]
            param=vec[1]
        if len(last_posi)==0:
            last_posi=cur_posi
        else:
            dist = get_2d_dist(cur_posi, last_posi)
            cur_s=cur_s+dist
            s_path.append(cur_s)
        path_posi.append(cur_posi)
        path_meta.append(param)
        if ":" in name:
            two_v = name.split("-")
            if len(two_v)==1:
                s_time=get_sec(two_v[0])
                e_time=get_sec(two_v[0])
            else:
                s_time=get_sec(two_v[0])
                e_time=get_sec(two_v[1])
            if last_s_time>s_time:
                return [False,"last_s_time>=s_time "+str(last_s_time)+" "+str(s_time)]
            last_s_time=s_time
            node_2_path.append([len(path_posi)-1, s_time, e_time])    
    
    seg_time_list=[]
    seg_pathid_list=[]
    for i in range(1, len(node_2_path)):
        seg_time_list.append([node_2_path[i-1][2], node_2_path[i][1]])
        seg_pathid_list.append([node_2_path[i-1][0], node_2_path[i][0]])

    path_seg_list=[]
    end_nodes=set()
    for i in range(len(seg_time_list)):
        if path_meta[seg_pathid_list[i][0]]=="end":
            continue
        seg_s_s=s_path[seg_pathid_list[i][0]]
        seg_e_s=s_path[seg_pathid_list[i][1]]
        seg_s=seg_e_s-seg_s_s
        seg_t_s=seg_time_list[i][0]
        seg_t_e=seg_time_list[i][1]
        seg_t=seg_t_e-seg_t_s
        for j in range(seg_pathid_list[i][0], seg_pathid_list[i][1]):
            s1=s_path[j]
            s2=s_path[j+1]
            t1 = (s1-seg_s_s)/seg_s*seg_t+seg_t_s
            t2 = (s2-seg_s_s)/seg_s*seg_t+seg_t_s
            seg={"time":[t1, t2],"posi":[path_posi[j],path_posi[j+1]],"meta":path_meta[j]}
            path_seg_list.append(seg)
        if path_meta[seg_pathid_list[i][1]]=="end":
            end_nodes.add(len(path_seg_list)-1)
            continue
    last_n=-1
    for i in range(img_count):
        cur_time=i/float(target_fps)
        posi,n = get_img_posi(cur_time, path_seg_list)
        if posi is not None:
            imgid_2_posi.append({"t":i, "p":posi,"meta":path_seg_list[n]["meta"]})
            last_n=n
        else:
            if n==-2:
                return [False,"time is equal: "+str(cur_time)]
            if last_n in end_nodes:
                imgid_2_posi[len(imgid_2_posi)-1]["meta"]="end"
    return [True,imgid_2_posi]

def get_frame_2_posi_seg(img_count, tmp_local):
    v_seg_frame_count=int(video_seg_length*60*target_fps)
    [re,imgid_2_posi]=get_img_2_posi_list(img_count, tmp_local)
    if re==False:
        return [False,imgid_2_posi]
    tmp_count=0
    v_seg_id=0
    imgid_2_posi_seg={}
    for item in imgid_2_posi:
        if v_seg_id not in imgid_2_posi_seg:
            imgid_2_posi_seg[v_seg_id]=[]
        imgid_2_posi_seg[v_seg_id].append(item)
        if tmp_count<v_seg_frame_count or len(imgid_2_posi)-tmp_count<2*v_seg_frame_count:
            pass
        else:
            tmp_count=0
            v_seg_id=v_seg_id+1
        if item["meta"]=="end":
            tmp_count=0
            v_seg_id=v_seg_id+1
        tmp_count=tmp_count+1
    return [True, imgid_2_posi_seg]

def get_task_list(task, mydb):
    task_list=[]
    for x in mydb[task_table_name].find({"task":task, "status":2},{"_id":0,"name":1}):
        task_list.append(x["name"])
    return task_list

def set_task_status(proj_name, task, status, info, mydb):
    myquery = { "name": proj_name }
    newvalues = { "$set": { "task": task, "status": status,"info":info} }
    mydb[task_table_name].update_one(myquery, newvalues, True)

def download_kml_oss(project_name, bucket, tmp_local):
    try:
        oss_path=oss_root+"/ws/"+project_name+"/chamo.kml"
        bucket.get_object_to_file(oss_path, tmp_local+"/chamo.kml")
    except:
        # print(traceback.format_exc())
        return [False,"download kml failed"]
    return [True,""]

def write_json_to_oss(data, oss_addr,pre, bucket):
    temp_file=pre+"temp_file.json"
    f = open(temp_file, "w")
    json.dump(data, f)
    f.close()
    bucket.put_object_from_file(oss_addr, temp_file)

def download_raw_video_oss(project_name, bucket, tmp_local):
    try:
        oss_path=oss_root+"/ws/"+project_name+"/chamo.mp4"
        bucket.get_object_to_file(oss_path, tmp_local+"/chamo.mp4")
    except:
        return [False,"download raw failed"]
    return [True,""]

def download_patches_oss(project_name, bucket, tmp_local):
    oss_prefix=oss_root+"/ws/"+project_name+"/"+patch_path
    patch_folder=tmp_local+"/"+patch_path
    if not os.path.exists(patch_folder):
        os.mkdir(patch_folder)
    try:
        for obj in oss2.ObjectIterator(bucket, prefix=oss_prefix+"/"):
            if ".jpg" in obj.key:
                tmp_v = obj.key.split("/")
                if len(tmp_v)!=6:
                    continue
                z_lev=tmp_v[4]
                patch_name=tmp_v[5]
                patch_z_path=patch_folder+"/"+z_lev
                if not os.path.exists(patch_z_path):
                    os.mkdir(patch_z_path)
                bucket.get_object_to_file(obj.key, patch_z_path+"/"+patch_name)
    except:
        return [False, "download patches failed"]
    return [True,""]

def upload_patch_to_oss(project_name, bucket, tmp_local):
    try:
        patch_folder=tmp_local+"/"+patch_path
        for d in os.listdir(patch_folder):
            if os.path.isfile(patch_folder+"/"+d):
                continue
            for d1 in os.listdir(patch_folder+"/"+d):
                if ".jpg" in d1:
                    patch_name=d+"/"+d1
                    oss_patch_path=oss_root+"/ws/"+project_name+"/"+patch_path+"/"+patch_name
                    if not bucket.object_exists(oss_patch_path):
                        local_patch_path=patch_folder+"/"+patch_name
                        bucket.put_object_from_file(oss_patch_path, local_patch_path)
    except:
        return [False, "upload patches failed"]
    return [True,""]

def upload_out_to_oss(project_name, bucket, tmp_local):
    try:
        for d in os.listdir(tmp_local):
            if not os.path.isfile(tmp_local+"/"+d):
                continue
            if (not "path_" in d) or (not ".mp4" in d):
                continue
            oss_patch_path=oss_root+"/video/"+project_name+"_"+d
            local_patch_path=tmp_local+"/"+d
            bucket.put_object_from_file(oss_patch_path, local_patch_path)
    except:
        return [False, "upload out failed"]
    return [True,""]

def get_video_frame_count(tmp_local):
    cmd = [
        "ffmpeg",
        "-i", tmp_local+"/chamo.mp4",
        "-f", "null", "-"
    ]
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    ffmpeg_duration_template = re.compile(r"time=\s*(\d+):(\d+):(\d+)\.(\d+)")
    result_all = ffmpeg_duration_template.findall(output.decode())
    if result_all:
        result = result_all[-1]
        duration = float(result[0]) * 60 * 60 \
                   + float(result[1]) * 60 \
                   + float(result[2]) \
                   + float(result[3]) * (10 ** -len(result[3]))
        duration=int(duration*25)
    else:
        duration = -1
    return duration 

def cal_whole_tiles(min_x, max_x, min_y, max_y):
    target_zoom = -1
    target_tiles_x = []
    target_tiles_y=[]
    for tmp_zoom in range(15,9,-1):
        z_diff=path_img_zoom-tmp_zoom
        wc_lt=[min_x>> z_diff, min_y>> z_diff]
        wc_rb=[max_x>> z_diff, max_y>> z_diff]
        wc_c=[(wc_rb[0]+wc_lt[0])/2, (wc_rb[1]+wc_lt[1])/2]
        wc_tile=[int(wc_c[0]//tile_size), int(wc_c[1]//tile_size)]
        
        if wc_rb[0]-wc_lt[0] > (wc_rb[1]-wc_lt[1])*1.51:
            base_len=wc_rb[0]-wc_lt[0]
            max_p=264
        else:
            base_len=wc_rb[1]-wc_lt[1]
            max_p=175
        if base_len<max_p-10:
            target_tiles_x=[wc_tile[0]-1,wc_tile[0],wc_tile[0]+1]
            target_tiles_y=[wc_tile[1]-1,wc_tile[1],wc_tile[1]+1]
            target_zoom=tmp_zoom
            break
    return target_zoom, target_tiles_x, target_tiles_y