# 上海海事大学数字平台监控

自动抓取 [my.shmtu.edu.cn](https://my.shmtu.edu.cn) 数字平台信息，通过 AI 概括后推送到微信。

## 功能

- 监控 14 个栏目（部门通知公告、教务公告、学术活动、讲座活动等）
- 自动点击文章标题，在新标签页提取全文
- DeepSeek AI 生成文章摘要
- PushPlus 推送到微信
- 过滤 3 个月前旧文
- 自动去重（已见文章不重复推送）

## 安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Chromium 浏览器（Playwright 需要）
playwright install chromium

# 3. 填写配置
cp config.json.example config.json
# 编辑 config.json，填入你的学号、密码、PushPlus Token、DeepSeek API Key
```

## 配置

编辑 `config.json`：

```json
{
    "username": "你的学号或工号",
    "password": "你的统一认证密码",
    "pushplus_token": "你的PushPlus Token",
    "deepseek_api_key": "你的DeepSeek API Key"
}
```

### 获取 Token

| 服务 | 说明 |
|------|------|
| **PushPlus** | 微信关注公众号「pushplus 推送加」→ 访问 [pushplus.plus](http://www.pushplus.plus) → 获取 token |
| **DeepSeek** | 访问 [platform.deepseek.com](https://platform.deepseek.com) → 创建 API Key |

## 使用

```bash
# 探索模式（快速查看各栏目文章数）
python main.py --discover

# 完整运行（抓取 + AI概括 + 微信推送）
python main.py

# 测试推送通道
python main.py --test

# 清除登录缓存
python main.py --reset
```

## 定时运行

### Windows

```bash
python main.py --setup
```

创建每天 8:00 执行的计划任务。可在「任务计划程序」中修改。

### Linux / macOS

```bash
# crontab -e
0 8 * * * cd /path/to/shmtu-monitor && python main.py
```

## 工作流程

```
CAS 登录 → Playwright 打开门户 → 逐栏目点击 → 逐篇打开文章
→ 提取全文 → DeepSeek AI 概括 → PushPlus 推送到微信
```

## 项目结构

```
├── config.json          # 配置文件（唯一需要编辑的文件）
├── config.py            # 从 JSON 读取配置
├── auth.py              # CAS 统一认证登录
├── scraper.py           # Playwright 抓取 + 全文提取
├── summarizer.py        # DeepSeek AI 概括
├── storage.py           # 本地去重
├── notifier.py          # PushPlus 微信推送
├── main.py              # 主入口
└── requirements.txt     # Python 依赖
```

## 注意事项

- 需在校园网或 VPN 环境下运行
- 首次运行需手动输入验证码
- 抓取 139 篇文章约需 5-10 分钟
- 每日推送控制在 20000 字以内（PushPlus 限制）

## License

MIT
