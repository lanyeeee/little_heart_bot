# 直接部署
理论上你能按照以下思路让小心心bot跑在linux之外的操作系统上，但我没试过  

## 前提
| Requirement |
| ----------- |
| python      |
| node.js     |
| mysql       |

## 开始部署
### 1.创建数据库并进入
```
在mysql下

create database little_heart;

use little_heart;
```
### 2.建表
**bot_info**
```
CREATE TABLE `bot_info` (
  `uid` bigint NOT NULL COMMENT 'uid',
  `cookie` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'cookie',
  `dev_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'dev_id',
  `app_status` int NOT NULL DEFAULT '0' COMMENT '0 normal, -1 cooling',
  `receive_status` int NOT NULL DEFAULT '0' COMMENT '0 normal, -1 cooling',
  `send_status` int NOT NULL DEFAULT '0' COMMENT '0 normal, -1 cooling, -2 forbidden',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**clients_info**
```
CREATE TABLE `clients_info` (
  `uid` bigint NOT NULL COMMENT 'uid',
  `cookie` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'cookie',
  `auto_gift` int DEFAULT '0' COMMENT '0 disable,1 enable',
  `completed` int DEFAULT '0' COMMENT 'completed or not',
  `room_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'little heart sent there',
  `target_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'little heart sent there',
  `target_name` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'target name',
  `cookie_status` int DEFAULT '0' COMMENT '0 unknow,1 normal,-1 error',
  `medal_status` int DEFAULT '0' COMMENT '0 narmal,-1 without,-2 error',
  `config_num` int DEFAULT '0' COMMENT 'how many times the client check the config today',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**messages_info**
```
CREATE TABLE `messages_info` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'primary key',
  `uid` bigint NOT NULL COMMENT 'uid',
  `target_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'target id',
  `target_name` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'target name',
  `room_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'room id',
  `content` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'content',
  `msg_status` int DEFAULT '0' COMMENT '0 unfinished,1 completed,-1 msg invalid,-2 UL error,-3 cookie invalid,-4 without room',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=171 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**sessions_info**
```
CREATE TABLE `sessions_info` (
  `uid` bigint NOT NULL COMMENT 'uid',
  `timestamp` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT '0' COMMENT 'latest receive',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
### 3.填写账号信息
```
insert into bot_info(uid) values(自己填);  

update bot_info set dev_id = 自己填;  

update bot_info set cookie = 自己填;  

quit;
```  
**关于dev_id**  
随便找个人私聊，找send_msg包，payload里有一项msg[dev_id]，里边的内容就是dev_id  

**务必确保所填信息是正确的** 

### 4.初始化Bilibili Heartbeat Server
```
在bilibili-pcheartbeat文件夹下

npm install
```
### 5.修改app.py和bot.py中连接mysql的部分
```
源码中连接mysql的部分为:

db = pymysql.connect(host='localhost', user='root', database='little_heart', autocommit=True, unix_socket='/var/run/mysqld/mysqld.sock')

请按你的情况进行修改
```
### 6.运行
**运行Bilibili Heartbeat Server**  
```
在bilibili-pcheartbeat文件夹下

node app.js
```
**运行小心心bot**  
分别用python运行bot.py和app.py即可  

总共是一个node和两个python
至此就部署完成了