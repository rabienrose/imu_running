from lxml import etree
import urllib.request
from PIL import Image 
from PIL import ImageDraw, ImageFont
import math
import shutil
import os
import time
import random
from chamo_common.util import get_frame_2_posi_seg
from chamo_common.util import get_bounding_box
from chamo_common.util import download_patches_oss
from chamo_common.util import get_task_list
from chamo_common.util import set_task_status
from chamo_common.util import download_kml_oss
from chamo_common.util import download_raw_video_oss
from chamo_common.util import cal_whole_tiles
from chamo_common.util import upload_out_to_oss
from chamo_common.util import get_sec
from chamo_common.util import write_json_to_oss
from chamo_common.util import download_res_oss
from chamo_common.config import get_oss_mongo
import oss2
import datetime
from datetime import date
import traceback
import chamo_common.config
path_img_zoom=chamo_common.config.path_img_zoom
tile_size=chamo_common.config.tile_size
patch_path=chamo_common.config.patch_path
tmp_local=tmp_local="tmp_file_cover"
task_table_name=chamo_common.config.task_table_name
target_fps=chamo_common.config.target_fps
oss_root=chamo_common.config.oss_root

center_img_xy=[5,40]
title_1_xy=[15,12]
whole_cover_size=[148,200]
center_img_size = [136,120]
text_bg_size=[22,80]
text_bg_center=[74,101]

if __name__ == '__main__':
    bucket, mydb = get_oss_mongo()
    download_res_oss(bucket)    
    while True:
        tasks=get_task_list("chamo", mydb)
        for task_name in tasks:
            try:
                print(task_name+" start")
                set_task_status(task_name, "cover_s",1,"", mydb)
                if os.path.exists(tmp_local):
                    shutil.rmtree(tmp_local)
                os.mkdir(tmp_local)
                try:
                    oss_path=oss_root+"/ws/"+task_name+"/cover.txt"
                    bucket.get_object_to_file(oss_path, tmp_local+"/cover.txt")
                except:
                    set_task_status(task_name, "cover",-2,"download raw failed",mydb)
                    continue
                try:
                    f = open(tmp_local+"/cover.txt","r")
                    lines = f.readlines()
                    txt_list=[]
                except:
                    set_task_status(task_name, "cover",-3,"has no cover.txt",mydb)
                    continue
                try:
                    broke_line=""
                    cover_infos=[]
                    for line in lines:
                        vec = line.split(",")
                        if len(vec)!=6:
                            broke_line=line
                            break
                        info={}
                        info["video_ind"]=vec[0]
                        info["video_title1"]=vec[1]
                        info["video_title2"]=vec[2]
                        info["time_stamp"]=vec[3]
                        info["img_name"]=vec[4]
                        txt_list.append(info)
                    if broke_line!="":
                        set_task_status(task_name, "cover",-4,broke_line,mydb)
                        continue
                except:
                    var = traceback.format_exc()
                    set_task_status(task_name, "cover",-5,var,mydb)
                    continue
                non_exist_img=""
                all_has_img=True
                for item in txt_list:
                    if item["img_name"]!="":
                        oss_path=oss_root+"/ws/"+task_name+"/imgs/"+item["img_name"]
                        try:
                            bucket.get_object_to_file(oss_path, tmp_local+"/"+item["img_name"])
                        except:
                            non_exist_img=item["img_name"]
                            break
                    else:
                        all_has_img=False
                
                if non_exist_img!="":
                    set_task_status(task_name, "cover",-7,non_exist_img,mydb)
                    continue
                if all_has_img==False:
                    [re,info] = download_raw_video_oss(task_name, bucket, tmp_local)
                    if re==False:
                        set_task_status(task_name, "cover",-8,info,mydb)
                        continue
                try:
                    fnt1 = ImageFont.truetype("res/text.ttf", 15)
                    fnt2 = ImageFont.truetype("res/text.ttf", 25)
                    for item in txt_list:
                        if "time_stamp" in item:
                            time_sec = get_sec(item["time_stamp"])
                            cmd="ffmpeg -y -ss "+str(time_sec)+" -i "+tmp_local+"/chamo.mp4 -vframes 1 "+tmp_local+"/frame.jpg"
                            os.system(cmd)
                            frame = Image.open(tmp_local+"/frame.jpg")
                            width, height=frame.size
                            frame=frame.resize((int(width*center_img_size[1]/height),center_img_size[1]))
                            width, height=frame.size
                            edge_w= int((width-center_img_size[0])/2)
                            center_img=frame.crop((edge_w, 0, width-edge_w, center_img_size[1]))
                        else:
                            center_img = Image.open(tmp_local+"/"+item["img_name"])
                        cover_img = Image.new('RGBA', (whole_cover_size[0],whole_cover_size[1]),(255, 255, 255, 0))
                        cover_img.paste(center_img,(center_img_xy[0], center_img_xy[1]))
                        cover_frame = Image.open("res/cover_frame.png")
                        cover_img.paste(cover_frame,(0, 0),cover_frame)
                        text_bg_img=Image.open("res/text_bg.png")
                        text_bg_ori=[text_bg_center[0]-int(text_bg_size[0]/2), text_bg_center[1]-int(text_bg_size[1]/2)]
                        cover_img.paste(text_bg_img,(text_bg_ori[0],text_bg_ori[1]),text_bg_img)
                        draw = ImageDraw.Draw(cover_img)
                        t2_len=len(item["video_title2"])*25
                        draw.text((74-int(t2_len/2),9), item["video_title2"], font=fnt2, fill=(255,255,255,255))
                        t2_count=len(item["video_title1"])
                        t2_size=t2_count*15
                        t=text_bg_center[1]-int(t2_size/2)
                        l=text_bg_center[0]-7
                        for i in range(t2_count):
                            draw.text((l, t+15*i), item["video_title1"][i], font=fnt1, fill=(255,255,255,255))
                        cover_img_name=task_name+"_patch_"+item["video_ind"]+".png"
                        cover_img.save(tmp_local+"/"+cover_img_name)
                        oss_path=oss_root+"/cover/"+cover_img_name
                        bucket.put_object_from_file(oss_path, tmp_local+"/"+cover_img_name)
                except:
                    var = traceback.format_exc()
                    set_task_status(task_name, "cover",-9,var,mydb)
                    continue
                
                set_task_status(task_name, "cover",2, "" ,mydb)
            except Exception as e:
                set_task_status(task_name, "cover",-999, "crash",mydb)
                var = traceback.format_exc()
                obj={"traj":task_name,"stack":var}
                now = datetime.datetime.now()
                date_created=now.strftime('%Y-%m-%d_%H-%M-%S')
                path = oss_root+"/err/"+date_created+"_cover_"+task_name+".txt"
                write_json_to_oss(obj,path,"cover",bucket)
        time.sleep(10)
