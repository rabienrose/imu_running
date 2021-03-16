from lxml import etree
import urllib.request
from PIL import Image 
from PIL import ImageDraw, ImageFont
from chamo_common.config import get_oss_mongo
from chamo_common.util import get_task_list
from chamo_common.util import set_task_status
from chamo_common.util import download_kml_oss
from chamo_common.util import download_raw_video_oss
from chamo_common.util import get_video_frame_count
from chamo_common.util import get_frame_2_posi_seg
from chamo_common.util import get_bounding_box
from chamo_common.util import download_patches_oss
from chamo_common.util import upload_patch_to_oss
from chamo_common.util import cal_whole_tiles
import chamo_common.config
import math
import shutil
import os
import time
import random
path_img_zoom=chamo_common.config.path_img_zoom
tile_size=chamo_common.config.tile_size
patch_path=chamo_common.config.patch_path
tmp_local=tmp_local=tmp_local="tmp_file_patch"
task_table_name=chamo_common.config.task_table_name

def download_whole_map(min_x, max_x, min_y, max_y, project_folder, path_info):
    patch_folder=tmp_local+"/"+patch_path
    if not os.path.exists(patch_folder):
        os.mkdir(patch_folder)
    target_zoom, target_tiles_x, target_tiles_y = cal_whole_tiles(min_x, max_x, min_y, max_y)
    if target_zoom==-1:
        return [False, "can not get target_zoom"]
    sub_patch_folder=patch_folder+"/"+str(target_zoom)
    if not os.path.exists(sub_patch_folder):
        os.mkdir(sub_patch_folder)
    for tile_x in target_tiles_x:
        for tile_y in target_tiles_y:
            file_name=sub_patch_folder+"/"+str(tile_x)+"_"+str(tile_y)+".jpg"
            if not os.path.exists(file_name):
                url = 'https://mt0.google.com/vt/lyrs=s&?x='+str(tile_x)+'&y='+str(tile_y)+'&z='+str(target_zoom)
                while True:
                    try:
                        urllib.request.urlretrieve(url, file_name)
                        break
                    except:
                        time.sleep(10)
                a = random.randint(10,20)
                time.sleep(a)
    return [True,""]

def download_img_path(img_posis):
    patch_folder=tmp_local+"/"+patch_path
    if not os.path.exists(patch_folder):
        os.mkdir(patch_folder)
    sub_patch_folder=patch_folder+"/"+str(path_img_zoom)
    if not os.path.exists(sub_patch_folder):
        os.mkdir(sub_patch_folder)
    path_list=[]
    for item in img_posis:
        path_list.append(item["p"])
    for xy in path_list:
        [tile_x, tile_y] = [xy[0]//tile_size, xy[1]//tile_size]
        for i in [-1,0,1]:
            for j in [-1,0,1]:
                tmp_tile_x=tile_x+i
                tmp_tile_y=tile_y+j
                file_name=sub_patch_folder+"/"+str(tmp_tile_x)+"_"+str(tmp_tile_y)+".jpg"
                if not os.path.exists(file_name):
                        url = 'https://mt0.google.com/vt/lyrs=s&?x='+str(tmp_tile_x)+'&y='+str(tmp_tile_y)+'&z='+str(path_img_zoom)
                        while True:
                            try:
                                urllib.request.urlretrieve(url, file_name)
                                break
                            except:
                                time.sleep(10)
                        a = random.randint(10,20)
                        time.sleep(a)
    return [True,""]

if __name__ == '__main__':
    bucket, mydb = get_oss_mongo()
    while True:
        tasks=get_task_list("count", mydb)
        for task_name in tasks:
            set_task_status(task_name, "patch",1,"",mydb)
            if os.path.exists(tmp_local):
                shutil.rmtree(tmp_local)
            os.mkdir(tmp_local)
            print(task_name+" start")
            [re,info]=download_kml_oss(task_name, bucket, tmp_local)
            if re==False:
                set_task_status(task_name, "patch",-2,info,mydb)
                continue
            for x in mydb[task_table_name].find({"name":task_name},{"_id":0,"frame_count":1}):
                if not "frame_count" in x:
                    set_task_status(task_name, "patch",-3,"no frame count",mydb)
                    continue
                img_count=x["frame_count"]
                [re,imgid_2_posi_seg] = get_frame_2_posi_seg(img_count)
                [re,info] = download_patches_oss(task_name, bucket, tmp_local)
                if re==False:
                    set_task_status(task_name, "patch",-4,info,mydb)
                    continue
                for key in imgid_2_posi_seg:
                    box = get_bounding_box(imgid_2_posi_seg[key])# left, right, bottom, top
                    [re,info]=download_img_path(imgid_2_posi_seg[key])
                    if re==False:
                        set_task_status(task_name, "patch",-8,info,mydb)
                        continue
                    [re,info]=download_whole_map(box[0], box[1], box[2], box[3], key,imgid_2_posi_seg[key])
                    if re==False:
                        set_task_status(task_name, "patch",-6,info,mydb)
                        continue
            upload_patch_to_oss(task_name, bucket, tmp_local)
            [re,info] = download_patches_oss(task_name, bucket, tmp_local)
            if re==False:
                set_task_status(task_name, "patch",-8,info,mydb)
                continue
            set_task_status(task_name, "patch",2,"",mydb)
        time.sleep(10)

    