#ip="47.88.86.187" #us
#ip="39.105.230.163" #beijing

# scp video_process.py root@39.105.230.163:~/imu_running
scp -r chamo_common root@39.105.230.163:~/imu_running
scp -r static root@39.105.230.163:~/imu_running
scp *.py root@39.105.230.163:~/imu_running
# scp *.sh root@47.88.86.187:~/imu_running

# scp download_pathes.py root@47.89.217.129:~/imu_running