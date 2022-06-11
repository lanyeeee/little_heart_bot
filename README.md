<p align="center">
<img src="img/little_heart.png">
<h3 align="center">小心心bot</h3>


# 这个版本已弃用，新版在编写中
# 简介
部署成功后你也能成为小心心bot

# 使用方法
https://www.bilibili.com/read/cv15257459?spm_id_from=333.999.0.0

# 部署依赖
| Requirement |
| ----------- |
| python      |
| node.js     |
| mysql       |

按理说在windows上跑也没问题，但我没试过

# 部署方式
 - [Docker 部署(推荐)](md/docker.md)   

 - [直接部署](md/direct.md)

# 感谢
- [bilibili-pcheartbeat](https://github.com/lkeme/bilibili-pcheartbeat)

# 注意
- app.py和bot.py全部使用requests进行同步请求而不采用更高效的异步是有意为之，意在避免并发，对B站api的请求过于频繁会导致ip被ban。  

- 如果遇到私信发不出去，code=21024,message=你发消息的频率太高了，停下来休息一下吧。不建议干等。最好去找人工客服解决。  
![](/img/staff1.png)
![](/img/staff2.png)

# License 许可证
[GPL v3](LICENSE)
