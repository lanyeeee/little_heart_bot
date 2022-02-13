# docker 部署

## 前提  
- 操作系统：linux amd(绝大多数) 或 linux arm(树莓派等单片机)  

- 装好docker，且docker能正常使用  

## 开始部署
### 1.拉取镜像
```
如果你的操作系统是 linux amd
docker pull lanyeeee/little_heart:amd

如果你的操作系统是 linux arm
docker pull lanyeeee/little_heart:amd
```
### 2.启动容器
```
如果你的操作系统是 linux amd
docker run -it lanyeeee/little_heart:amd

如果你的操作系统是 linux arm
docker run -it lanyeeee/little_heart:arm
```
### 3.填写账号信息
```
mysql  

use little_heart;

insert into bot_info(uid) values(自己填);

update bot_info set dev_id = 自己填;

update bot_info set cookie = 自己填;

quit;
```  
**关于dev_id**  
随便找个人私聊，找send_msg包，payload里有一项msg[dev_id]，里边的内容就是dev_id  

**务必确保所填信息是正确的** 

### 4.运行小心心bot
```
cd /home  

sh start.sh
```
### 5.查看是否正确运行
```
ps
```
列表里应有两个python3和一个node，如下面所示
```
PID TTY          TIME   CMD
    1 pts/0    00:00:00 sh
    7 pts/0    00:00:00 sh
319 pts/0    00:00:00 bash
324 pts/0    00:00:00 python3
325 pts/0    00:00:00 python3
326 pts/0    00:00:01 node
334 pts/0    00:00:00 ps
```


## 日志
保存在/home/log里  

