<p align="center">
<img src="img/little_heart.png">
<h3 align="center">小心心bot</h3>

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
app.py和bot.py全部使用requests进行同步请求是有意为之，意在降低程序执行的效率，因为对B站api的请求过于频繁会导致ip被ban

# License 许可证
[GPL v3](LICENSE)