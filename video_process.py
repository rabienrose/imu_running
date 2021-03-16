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
from chamo_common.config import get_oss_mongo
import chamo_common.config
path_img_zoom=chamo_common.config.path_img_zoom
tile_size=chamo_common.config.tile_size
patch_path=chamo_common.config.patch_path
tmp_local=tmp_local="tmp_file_proc"
task_table_name=chamo_common.config.task_table_name
target_fps=chamo_common.config.target_fps

def extract_video():
    in_imgs_folder=tmp_local+"/in_video_imgs"
    if os.path.exists(in_imgs_folder):
        shutil.rmtree(in_imgs_folder)
    os.mkdir(in_imgs_folder)
    video_file=tmp_local+"/chamo.mp4"
    cmd_str2 = "ffmpeg -i "+video_file+' -qscale:v 3 -vf scale="-1:720,fps='+str(target_fps)+'" '+in_imgs_folder+"/%06d.jpg"
    os.system(cmd_str2)
    return [True, ""]

def stitch_img_aera(min_x, max_x, min_y, max_y):
    sub_patch_folder=tmp_local+"/"+patch_path+"/"+str(path_img_zoom)
    if not os.path.exists(sub_patch_folder):
        return [False, "patch folder not exist"]
    tiles_lt = [min_x//tile_size, min_y//tile_size]
    tiles_lt[0]=tiles_lt[0]-1
    tiles_lt[1]=tiles_lt[1]-1
    tiles_rb = [max_x//tile_size, max_y//tile_size]
    tiles_rb[0]=tiles_rb[0]+1
    tiles_rb[1]=tiles_rb[1]+1
    width=(tiles_rb[0] - tiles_lt[0]+1)*tile_size
    height=(tiles_rb[1] - tiles_lt[1]+1)*tile_size
    map_img = Image.new('RGB', (width,height))
    for tile_x in range(tiles_lt[0], tiles_rb[0]+1):
        for tile_y in range(tiles_lt[1], tiles_rb[1]+1):
            file_name=sub_patch_folder+"/"+str(tile_x)+"_"+str(tile_y)+".jpg"
            if os.path.exists(file_name):
                im = Image.open(file_name).convert('RGB')
                map_img.paste(im, ((tile_x-tiles_lt[0])*tile_size, (tile_y-tiles_lt[1])*tile_size))
            else:
                return [False, "path patch not exsit"]
    for item in os.listdir(tmp_local):
        if "wholemap_" in item and "big" in item:
            os.remove(tmp_local+"/"+item)
    map_img.save(tmp_local+"/"+"wholemap"+"_"+str(tiles_lt[0]*tile_size)+"_"+str(tiles_lt[1]*tile_size)+"_"+str(path_img_zoom)+"_big.jpg")
    return [True, ""]

def stitch_whole_map(min_x, max_x, min_y, max_y, path_info):
    target_zoom, target_tiles_x, target_tiles_y = cal_whole_tiles(min_x, max_x, min_y, max_y)
    if target_zoom==-1:
        return [False, "can not get target_zoom"]
    sub_patch_folder=tmp_local+"/"+patch_path+"/"+str(target_zoom)
    width=3*tile_size
    height=3*tile_size
    map_img = Image.new('RGB', (width,height))
    for tile_x in target_tiles_x:
        for tile_y in target_tiles_y:
            file_name=sub_patch_folder+"/"+str(tile_x)+"_"+str(tile_y)+".jpg"
            if os.path.exists(file_name):
                im = Image.open(file_name).convert('RGB')
                map_img.paste(im, ((tile_x-target_tiles_x[0])*tile_size, (tile_y-target_tiles_y[0])*tile_size))
            else:
                return [False, "whole patch not exsit"]
    pts=[]
    for i in range(len(path_info)):
        z_diff=path_img_zoom-target_zoom
        [x,y]=[path_info[i]["p"][0]>> z_diff, path_info[i]["p"][1]>> z_diff]
        [x_img,y_img]=[x-target_tiles_x[0]*tile_size,y-target_tiles_y[0]*tile_size]
        pts.append((x_img,y_img))
    draw = ImageDraw.Draw(map_img)
    draw.line(pts,fill=(255,0,0,255),width=9)
    for item in os.listdir(tmp_local):
        if "wholemap_" in item and "small" in item:
            os.remove(tmp_local+"/"+item)
    map_img.save(tmp_local+"/"+"wholemap_"+str(target_tiles_x[0]*tile_size)+"_"+str(target_tiles_y[0]*tile_size)+"_"+str(target_zoom)+"_small.jpg")
    return [True, ""]

def get_map_crop_img(center, s, whole_map,image_ori):
    left=center[0]-s-image_ori[0]
    right=center[0]+s-image_ori[0]
    up=center[1]-s-image_ori[1]
    below=center[1]+s-image_ori[1]
    return whole_map.crop((left, up, right, below))

def gen_video_imgs(imgid_2_posi):
    image_ori=[0,0]
    s_image_ori=[0,0]
    whilemap_name=""
    s_whilemap_name=""
    in_video_imgs_folder=tmp_local+"/in_video_imgs"
    if not os.path.exists(in_video_imgs_folder):
        return [False, "no in_video_imgs_folder"]
    for item in os.listdir(tmp_local):
        if "wholemap_" in item and "big" in item:
            whilemap_name=tmp_local+"/"+item
            vec=item.split("_")
            image_ori[0]=int(vec[1])
            image_ori[1]=int(vec[2])
            image_zoom=int(vec[3])
        if "wholemap_" in item and "small" in item:
            s_whilemap_name=tmp_local+"/"+item
            vec=item.split("_")
            s_image_ori[0]=int(vec[1])
            s_image_ori[1]=int(vec[2])
            s_image_zoom=int(vec[3])
    if whilemap_name=="":
        return [False, "no whole mapimg"]
    if s_whilemap_name=="":
        return [False, "no small whole mapimg"]
    out_video_imgs_folder=tmp_local+"/out_video_imgs"
    if os.path.exists(out_video_imgs_folder):
        shutil.rmtree(out_video_imgs_folder)
    os.mkdir(out_video_imgs_folder)
    Image.MAX_IMAGE_PIXELS = None
    map_whole = Image.open(whilemap_name)
    s_map_whole = Image.open(s_whilemap_name)
    s_map_whole = s_map_whole.resize((256, 256))
    
    img_cont=0
    last_dir=[0,0]
    last_angle=0
    last_change_frame=0
    last_mode="world"
    for i in range(len(imgid_2_posi)):
        img_filename=str(1000000+imgid_2_posi[i]["t"]+1)[1:7]+".jpg"
        img_path=in_video_imgs_folder+"/"+img_filename
        if not os.path.exists(img_filename):
            continue
        im = Image.open(img_path)
        width, height = im.size
        
        if width/height>1.77777777778:
            im=im.resize((int(width*640/height),640))
            width, height = im.size
            left=int((width-1138)/2)
            im = im.crop((left, 0, width-left, 640))
        else:
            im=im.resize((1138,int(height*1138/width)))
            width, height = im.size
            top=int((height-640)/2)
            im = im.crop((0, top, 1138, height-top))
        cropped = get_map_crop_img(imgid_2_posi[i]["p"], 256, map_whole, image_ori)
        angle=0
        angle_avg=200
        
        if i+angle_avg<len(imgid_2_posi):
            cur_dir =[imgid_2_posi[i+angle_avg]["p"][0]-imgid_2_posi[i]["p"][0], imgid_2_posi[i+angle_avg]["p"][1]-imgid_2_posi[i]["p"][1]]
            dir=[0.05*cur_dir[0]+0.95*last_dir[0], 0.05*cur_dir[1]+0.95*last_dir[1]]
            angle_rad = math.atan2(dir[1], dir[0])
            last_dir=dir
            angle=angle_rad*180/3.1415926
        else:
            angle = last_angle
        angle_diff=abs(angle-last_angle)
        if angle_diff>10:
            angle_diff=0
        change_time_thresh=500
        if abs(angle-last_angle)<0.1 and (img_cont-last_change_frame>change_time_thresh and last_mode=="world" or last_mode=="local") or abs(angle-last_angle)>=0.1 and img_cont-last_change_frame<change_time_thresh and last_mode=="local":
            cropped=cropped.rotate(angle+90)
            cropped=cropped.crop((128, 128, 384, 384))
            cropped.putalpha(200)
            width, height = im.size
            im.paste(cropped, (0, height-256), mask=cropped)
            if last_mode=="world":
                last_change_frame=img_cont
                last_mode="local"
        else:
            s_map_whole_t = s_map_whole.copy() 
            draw = ImageDraw.Draw(s_map_whole_t)
            [x,y]=imgid_2_posi[i]["p"]
            z_diff=image_zoom-s_image_zoom
            [x_s,y_s]=[(x>> z_diff) - s_image_ori[0], (y>> z_diff) - s_image_ori[1] ]
            [x_s,y_s]=[int(x_s/3),int(y_s/3)]
            draw.ellipse((x_s-5, y_s-5, x_s+5, y_s+5), fill = 'blue', outline ='blue')
            s_map_whole_t.putalpha(200)
            im.paste(s_map_whole_t, (0, height-256), mask=s_map_whole_t)
            if last_mode=="local":
                last_change_frame=img_cont
                last_mode="world"
        draw = ImageDraw.Draw(im)
        fnt = ImageFont.truetype("Montserrat-ExtraLight.otf", 20)
        time_sec = imgid_2_posi[i]["t"]/target_fps
        time_str=str(int(time_sec//60))+":"+str(int(time_sec-time_sec//60*60))
        draw.text((0,0), time_str, font=fnt, fill=(255,255,255,128))
        last_angle=angle
        img_filename=str(1000000+img_cont)[1:7]+".jpg"
        im.save(out_video_imgs_folder+"/"+img_filename)
        img_cont=img_cont+1
    return [True,""]

def convert_2_mp4(key):
    out_video_imgs_folder=tmp_local+"/out_video_imgs"
    if not os.path.exists(out_video_imgs_folder):
        return [False,"out video imgs not exist"]
    cmd="ffmpeg -i ./"+out_video_imgs_folder+"/%06d.jpg -vcodec libx264 -crf 28 -preset fast -pix_fmt yuv420p "+tmp_local+"/path_"+str(key)+".mp4"
    os.system(cmd)
    return [True, ""]

if __name__ == '__main__':
    bucket, mydb = get_oss_mongo()
    while True:
        tasks=get_task_list("patch", mydb)
        for task_name in tasks:
            set_task_status(task_name, "proc",1,"", mydb)
            if os.path.exists(tmp_local):
                shutil.rmtree(tmp_local)
            os.mkdir(tmp_local)
            print(task_name+" start")
            [re,info]=download_kml_oss(task_name, bucket, tmp_local)
            if re==False:
                set_task_status(task_name, "proc",-2,info,mydb)
                continue
            [re,info]=download_raw_video_oss(task_name, bucket, tmp_local)
            if re==False:
                set_task_status(task_name, "proc",-3,info,mydb)
                continue
            for x in mydb[task_table_name].find({"name":task_name},{"_id":0,"frame_count":1}):
                if not "frame_count" in x:
                    set_task_status(task_name, "proc",-4, "no frame count",mydb)
                    continue
                img_count=x["frame_count"]
                [re,imgid_2_posi_seg] = get_frame_2_posi_seg(img_count)
                if re==False:
                    set_task_status(task_name, "proc",-5,info,mydb)
                    continue
                [re,info]=download_patches_oss(task_name, bucket, tmp_local)
                if re==False:
                    set_task_status(task_name, "proc",-6,info,mydb)
                    continue
                [re,info]=extract_video()
                if re==False:
                    set_task_status(task_name, "proc",-7,info,mydb)
                    continue
                for key in imgid_2_posi_seg:
                    box = get_bounding_box(imgid_2_posi_seg[key])# left, right, bottom, top
                    [re,info]=stitch_img_aera(box[0], box[1], box[2], box[3])
                    if re==False:
                        set_task_status(task_name, "proc",-8,info,mydb)
                        continue
                    [re,info]=stitch_whole_map(box[0], box[1], box[2], box[3], imgid_2_posi_seg[key])
                    if re==False:
                        set_task_status(task_name, "proc",-9,info,mydb)
                        continue
                    [re,info]=gen_video_imgs(imgid_2_posi_seg[key])
                    if re==False:
                        set_task_status(task_name, "proc",-10,info,mydb)
                        continue
                    [re,info]=convert_2_mp4(key)
                    if re==False:
                        set_task_status(task_name, "proc",-11,info,mydb)
                        continue
                break
            [re,info]=upload_out_to_oss(task_name, bucket, tmp_local)
            if re==False:
                set_task_status(task_name, "patch",-2,info,mydb)
                continue
            set_task_status(task_name, "proc",2, info,mydb)
        time.sleep(10)
