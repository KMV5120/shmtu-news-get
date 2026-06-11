# 上海海事大学数字平台监控

自动抓取 [my.shmtu.edu.cn](https://my.shmtu.edu.cn) 数字平台信息，通过 DeepSeek AI 概括后推送到微信。

## 快速开始（推荐）

双击 `run.bat`，脚本会自动：

1. 检测 Python 是否安装
2. 检测依赖是否安装（缺失则自动 `pip install`）
3. 检测浏览器引擎（优先用系统 Edge，**无需下载 182MB Chromium**）
4. 检查 `config.json` 配置

首次使用只需编辑 `config.json` 填入信息：

```json
{
    "username": "你的学号或工号",
    "password": "你的统一认证密码",
    "pushplus_token": "你的PushPlus Token",
    "deepseek_api_key": "你的DeepSeek API Key"
}
```

## 手动安装

```bash
pip install -r requirements.txt

# 浏览器引擎（二选一）
# 方式 A：使用系统 Edge（推荐，零下载）
#   无需操作，run.bat 自动检测
#
# 方式 B：下载 Playwright Chromium（182MB）
python -m playwright install chromium
```

## 配置

| 服务 | 获取方式 |
|------|----------|
| **PushPlus** | 微信关注「pushplus 推送加」→ pushplus.plus → 获取 token |
| **DeepSeek** | platform.deepseek.com → 创建 API Key |

## 使用

```bash
python main.py                 # 完整运行（抓取 + AI 摘要 + 微信推送 + 保存 md）
python main.py --discover      # 探索模式（快速查看各栏目文章数）
python main.py --test          # 测试推送通道
python main.py --setup         # 安装定时任务（每周六 18:00）
```

也可以双击 `run.bat` 使用交互菜单。

## 输出

运行后会在终端醒目显示新增内容，同时在工作目录保存 `YYMMDDHHMM.md` 报告文件，内容包括：

- 🔴 **置顶**：新增条目（含标题、日期、链接、AI 摘要）
- 📊 **全部条目**：本次抓取的所有文章汇总

## 定时运行

```bash
python main.py --setup
```

创建每周六 18:00 执行的 Windows 计划任务。

## 项目结构

```
├── run.bat              # 一键启动（含环境检测 + 浏览器配置）
├── config.json          # 配置文件（唯一需要编辑的文件）
├── config.json.example  # 配置模板
├── config.py            # 从 JSON 读取配置
├── auth.py              # CAS 统一认证登录
├── scraper.py           # Playwright 抓取 + 全文提取
├── summarizer.py        # DeepSeek AI 概括
├── storage.py           # 本地去重（seen_items.json）
├── notifier.py          # PushPlus 微信推送
├── main.py              # 主入口
└── requirements.txt     # Python 依赖
```

## 注意事项

- 需在校园网或 VPN 环境下运行
- 首次运行需手动输入 CAS 验证码
- 监控 14 个栏目：部门通知公告、教务公告、学术活动、讲座活动等
- 自动过滤 3 个月前的旧文章

## License

MIT
