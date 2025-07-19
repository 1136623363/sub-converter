# sub-converter

## 项目简介

sub-converter 是一个基于 Flask 的多协议订阅聚合与转换平台，支持 Clash、Shadowrocket 等主流客户端的订阅格式自动识别与转换。支持订阅管理（增删改查）、一键复制订阅链接、自动识别客户端类型返回对应配置、分组展示、AJAX 弹窗操作、Docker 一键部署等。

## 主要功能

- 支持添加、编辑、删除、手动更新订阅
- 支持多协议订阅（Clash、Shadowrocket等）自动识别与分类
- 主页分组展示 Clash/Shadowrocket 订阅
- 一键复制统一订阅链接，自动识别客户端类型返回对应格式
- 订阅内容自动定时刷新
- 支持原始内容查看、订阅去重、异常处理
- 支持 Docker、docker-compose 一键部署
- 支持 sqlite 数据持久化
- 现代化前端（Bootstrap5，弹窗、toast、AJAX）

## 目录结构

```
sub-converter/
├── app/
│   ├── app.py              # Flask 主应用入口
│   ├── converter.py        # 订阅内容抓取、解析与格式转换
│   ├── models.py           # 数据库模型定义
│   ├── scheduler.py        # 定时任务（自动刷新订阅）
│   ├── utils.py            # 工具函数
│   └── templates/          # 前端模板（index.html, base.html, subscribe.html 等）
│       ├── base.html
│       ├── index.html
│       └── subscribe.html
├── requirements.txt        # Python 依赖
├── dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
└── README.md               # 项目说明
```

## 主要页面与接口

- `/`         ：主页，订阅管理、分组展示、操作入口
- `/sub`      ：统一订阅接口，自动识别客户端类型返回 Clash 或 Shadowrocket 格式
- `/add`      ：添加订阅（POST）
- `/edit/<id>`：编辑订阅
- `/delete/<id>`：删除订阅
- `/update/<id>`：手动刷新订阅内容
- `/raw/<id>` ：查看原始订阅内容
- `/subscribe`：订阅链接展示页

## 快速部署

1. 构建镜像
   ```sh
   docker-compose build
   ```
2. 启动服务
   ```sh
   docker-compose up -d
   ```
3. 访问 http://localhost:5000

## 其它说明
- 支持多机场订阅聚合，自动去重、自动补全 Clash 必需字段
- 支持定时自动刷新所有订阅
- 支持一键复制订阅链接，toast 居中提示
- 支持 sqlite 数据持久化，数据目录为 `app/data/`
- 支持 Docker 部署，推荐使用 docker-compose

---
如有问题或建议欢迎反馈！
