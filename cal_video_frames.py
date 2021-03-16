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
import chamo_common.config
import math
import shutil
import os
import time
import random
tmp_local="tmp_file_count"
task_table_name=chamo_common.config.task_table_name
if __name__ == '__main__':
    bucket, mydb = get_oss_mongo()
    while True:
        tasks=get_task_list("init", mydb)
        for task_name in tasks:
            set_task_status(task_name, "count",1,"", mydb)
            if os.path.exists(tmp_local):
                shutil.rmtree(tmp_local)
            os.mkdir(tmp_local)
            print(task_name+" start")
            for x in mydb[task_table_name].find({"name":task_name},{"_id":0,"frame_count":1}):
                if not "frame_count" in x:
                    if download_raw_video_oss(task_name, bucket, tmp_local)==False:
                        set_task_status(task_name, "count",-3,"get video failed", mydb)
                        continue
                    img_count = get_video_frame_count(tmp_local)
                    mydb[task_table_name].update_one({"name":task_name},{"$set":{"frame_count":img_count}})
            set_task_status(task_name, "count",2,"", mydb)
        time.sleep(10)

    