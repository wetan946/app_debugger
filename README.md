# 车间生产看板系统

## 项目简介

这是一个基于 Flask 和 SQLite 的车间生产看板系统，旨在管理和展示工单进度。用户可以查看当前工单状态、更新工单进度、以及查看生产汇总信息。

## 系统功能

- 查看所有工单列表，支持按状态筛选（待生产、生产中、已完成）。
- 更新工单进度，自动根据进度更新工单状态。
- 获取今日生产汇总，包括工单状态数量、总计划产量、总完成产量、整体完成率。

## 技术栈

- **后端**：Flask（Python）
- **数据库**：SQLite
- **前端**：HTML, CSS, JavaScript

## 环境要求

- Python 3.7 及以上
- pip（Python 包管理工具）

## 安装与运行

### 1. 克隆仓库

首先，克隆这个项目到本地：

```bash
git clone https://github.com/wetan946/app_debugger.git
cd app_debugger

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

### 3. 激活虚拟环境
source venv/bin/activate

### 4. 安装依赖
```bash
pip install flask

### 5. 启动系统

```bash
python app_debug.py

### 6. 访问应用
在浏览器中访问http://127.0.0.1:5000/，你将看到车间生产看板页面，可以查看和更新工单进度。
