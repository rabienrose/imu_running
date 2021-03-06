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
tmp_local=tmp_local="tmp_file_proc"
task_table_name=chamo_common.config.task_table_name
target_fps=chamo_common.config.target_fps
oss_root=chamo_common.config.oss_root

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

def gen_video_imgs(imgid_2_posi, txt_list, box):
    image_ori=[0,0]
    s_image_ori=[0,0]
    whilemap_name=""
    s_whilemap_name=""
    in_video_imgs_folder=tmp_local+"/in_video_imgs"
    if not os.path.exists(in_video_imgs_folder):
        return [False, "no in_video_imgs_folder"]
    box_center=[int((box[0]+box[1])/2),int((box[2]+box[3])/2)]
    
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
    z_diff=image_zoom-s_image_zoom
    box_center=[(box_center[0]>> z_diff)-s_image_ori[0], (box_center[1]>> z_diff)-s_image_ori[1]]
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
    frame_name="res/frame.png"
    frame_border = Image.open(frame_name)
    width_b, height_b = frame_border.size
    me_marker = Image.open("res/me.png")
    cul_path_img_count=0
    
    img_cont=0
    last_dir=[0,0]
    fnt = ImageFont.truetype("res/Montserrat-ExtraLight.otf", 20)
    fnt1 = ImageFont.truetype("res/text.ttf", 36)
    fnt2 = ImageFont.truetype("res/text.ttf", 15)
    for i in range(len(imgid_2_posi)):
        img_filename=str(1000000+imgid_2_posi[i]["t"]+1)[1:7]+".jpg"
        img_path=in_video_imgs_folder+"/"+img_filename
        if not os.path.exists(img_path):
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
        cur_dir =imgid_2_posi[i]["dir"]
        dir=[0.01*cur_dir[0]+0.99*last_dir[0], 0.01*cur_dir[1]+0.99*last_dir[1]]
        angle_rad = math.atan2(dir[1], dir[0])
        last_dir=dir
        angle=angle_rad*180/3.1415926
        sub_img_type=""
        if i%1500==0:
            cul_path_img_count=100
        if cul_path_img_count>0:
            sub_img_type="path"
            s_map_whole_t = s_map_whole.copy() 
            pts_b=[]
            pts_f=[] 
            cur_posi=[]
            for j in range(0,len(imgid_2_posi), 100):
                [x,y]=[imgid_2_posi[j]["p"][0]>>z_diff, imgid_2_posi[j]["p"][1]>>z_diff]
                [x_img,y_img]=[x-s_image_ori[0],y-s_image_ori[1]]
                if j<i:
                    pts_b.append((x_img,y_img))
                else:
                    pts_f.append((x_img,y_img))
            draw = ImageDraw.Draw(s_map_whole_t)
            draw.line(pts_b,fill=(255,255,255,255),width=4)
            draw.line(pts_b,fill=(0xd8,0x58,0x52,255),width=2)
            draw.line(pts_f,fill=(255,255,255,178),width=4)
            cur_posi=[(imgid_2_posi[i]["p"][0]>>z_diff)-s_image_ori[0], (imgid_2_posi[i]["p"][1]>>z_diff)-s_image_ori[1]]
            s_map_whole_t.paste(me_marker, (cur_posi[0]-7,cur_posi[1]-7), mask=me_marker) 
            # draw.ellipse((cur_posi[0]-5, cur_posi[1]-5, cur_posi[0]+5, cur_posi[1]+5), fill = 'blue', outline ='blue')            
            s_map_whole_t=s_map_whole_t.crop((box_center[0]-132, box_center[1]-87, box_center[0]+132, box_center[1]+88))
            im.paste(s_map_whole_t, (44, height-195-24))
            cul_path_img_count=cul_path_img_count-1
        else:
            sub_img_type="bv"
            cropped=cropped.rotate(angle+90)
            cropped=cropped.crop((124, 168, 388, 344))
            # cropped.putalpha(200)
            width, height = im.size
            im.paste(cropped, (44, height-195-24))
        
        im.paste(frame_border, (34, height-24-height_b), mask=frame_border)
        draw = ImageDraw.Draw(im)
        
        time_sec = imgid_2_posi[i]["t"]/target_fps
        time_str=str(int(time_sec//60))+":"+str(int(time_sec-time_sec//60*60))
        draw.text((0,0), time_str, font=fnt, fill=(255,255,255,128))
        text=""
        for item in txt_list:
            if time_sec<item[1] and time_sec>item[0]:
                text=item[2]
                break
        if text !="":
            draw.text((351,510), text, font=fnt1, fill=(255,255,255,255))
        if sub_img_type=="bv":
            draw.text((int(176-3*15/2),598), "?????????", font=fnt2, fill=(255,255,255,255))
        elif sub_img_type=="path":
            draw.text((int(176-3*15/2),598), "?????????", font=fnt2, fill=(255,255,255,255))
        img_filename=str(1000000+img_cont)[1:7]+".jpg"
        im.save(out_video_imgs_folder+"/"+img_filename)
        img_cont=img_cont+1
    return [True,""]

def download_txt_oss(project_name):
    try:
        oss_path=oss_root+"/ws/"+project_name+"/chamo.txt"
        bucket.get_object_to_file(oss_path, tmp_local+"/chamo.txt")
    except:
        return [False,"download raw failed"]
    return [True,""]

def convert_2_mp4(key):
    out_video_imgs_folder=tmp_local+"/out_video_imgs"
    if not os.path.exists(out_video_imgs_folder):
        return [False,"out video imgs not exist"]
    cmd="ffmpeg -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -i ./"+out_video_imgs_folder+"/%06d.jpg -vcodec libx264 -crf 28 -preset fast -pix_fmt yuv420p -shortest "+tmp_local+"/path_"+str(key)+".mp4"
    os.system(cmd)
    return [True, ""]

def read_txt():
    try:
        f = open(tmp_local+"/chamo.txt","r")
        lines = f.readlines()
        txt_list=[]
    except:
        return [True, []]
    try:
        for line in lines:
            vec = line.split(",")
            if len(vec)!=3:
                return [False, "txt format wrong: "+line]
            time_str1=vec[0]
            time_str2=vec[1]
            content_str=vec[2]
            sec_s = get_sec(time_str1)
            sec_e = get_sec(time_str2)
            txt_list.append([sec_s, sec_e, content_str])
    except:
        return [False, "txt format wrong: "+line]
    return [True, txt_list]

if __name__ == '__main__':
    bucket, mydb = get_oss_mongo()
    download_res_oss(bucket)
    while True:
        tasks=get_task_list("patch", mydb)
        for task_name in tasks:
            try:
                print(task_name+" start")
                set_task_status(task_name, "proc",1,"", mydb)
                txt_list=[]

                # if os.path.exists(tmp_local):
                #     shutil.rmtree(tmp_local)
                # os.mkdir(tmp_local)
                # download_txt_oss(task_name)
                # [re,txt_list]=read_txt()
                # if re==False:
                #     set_task_status(task_name, "proc",-13,txt_list,mydb)
                #     continue
                # [re,info]=download_kml_oss(task_name, bucket, tmp_local)
                # if re==False:
                #     set_task_status(task_name, "proc",-2,info,mydb)
                #     continue
                # [re,info]=download_raw_video_oss(task_name, bucket, tmp_local)
                # if re==False:
                #     set_task_status(task_name, "proc",-3,info,mydb)
                #     continue
                # [re,info]=download_patches_oss(task_name, bucket, tmp_local)
                # if re==False:
                #     set_task_status(task_name, "proc",-6,info,mydb)
                #     continue
                # [re,info]=extract_video()
                # if re==False:
                #     set_task_status(task_name, "proc",-7,info,mydb)
                #     continue

                re = list(mydb[task_table_name].find({"name":task_name},{"_id":0,"frame_count":1}))
                if len(re)==0:
                    set_task_status(task_name, "proc",-4, "no frame count",mydb)
                    continue
                if not "frame_count" in re[0]:
                    set_task_status(task_name, "proc",-4, "no frame count",mydb)
                    continue
                img_count=re[0]["frame_count"]
                [re,imgid_2_posi_seg] = get_frame_2_posi_seg(img_count, tmp_local)
                if re==False:
                    set_task_status(task_name, "proc",-5,imgid_2_posi_seg,mydb)
                    continue
                
                b_succ=True
                for key in imgid_2_posi_seg:
                    box = get_bounding_box(imgid_2_posi_seg[key])# left, right, bottom, top

                    [re,info]=stitch_img_aera(box[0], box[1], box[2], box[3])
                    if re==False:
                        set_task_status(task_name, "proc",-8,info,mydb)
                        b_succ=False
                        break
                    [re,info]=stitch_whole_map(box[0], box[1], box[2], box[3], imgid_2_posi_seg[key])
                    if re==False:
                        set_task_status(task_name, "proc",-9,info,mydb)
                        b_succ=False
                        break

                    [re,info]=gen_video_imgs(imgid_2_posi_seg[key], txt_list, box)
                    if re==False:
                        set_task_status(task_name, "proc",-10,info,mydb)
                        b_succ=False
                        break
                    [re,info]=convert_2_mp4(key)
                    if re==False:
                        set_task_status(task_name, "proc",-11,info,mydb)
                        b_succ=False
                        break
                if b_succ==False:
                    continue

                # [re,info]=upload_out_to_oss(task_name, bucket, tmp_local)
                # if re==False:
                #     set_task_status(task_name, "patch",-12,info,mydb)
                #     continue

                set_task_status(task_name, "proc",2, "" ,mydb)
            except Exception as e:
                set_task_status(task_name, "proc",-999, "crash",mydb)
                var = traceback.format_exc()
                obj={"traj":task_name,"stack":var}
                now = datetime.datetime.now()
                date_created=now.strftime('%Y-%m-%d_%H-%M-%S')
                path = oss_root+"/err/"+date_created+"_proc_"+task_name+".txt"
                write_json_to_oss(obj,path,"proc",bucket)
        time.sleep(10)
