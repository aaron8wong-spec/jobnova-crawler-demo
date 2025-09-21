# JobNova Crawler Demo 项目使用文档

## 项目概述

这是一个基于 Scrapy 框架的网络爬虫项目，用于抓取招聘信息，特别是针对特定公司（如 Apple）的职位数据。项目使用 uv 作为 Python 包管理器，依赖包括 Scrapy、BeautifulSoup4、Elasticsearch 等，用于数据抓取、解析和存储。

项目结构：
- `pyproject.toml`：项目配置和依赖列表。
- `jobs/`：Scrapy 项目目录。
  - `spiders/`：爬虫文件，例如 `bs4_Apple.py`（Apple 职位爬虫）。
  - `settings.py`：Scrapy 配置，包括中间件、管道和自定义错误/标签设置。
  - `pipelines.py`：数据处理管道，使用 API 保存数据。
  - `items.py`：定义抓取项（JobsItem）。

当前实现支持抓取 Apple 职位，过滤最近 2 天内的职位，检查位置是否在监控范围内，并通过 API 分析标签。

## 环境要求

- Python >= 3.12
- uv（Python 包管理器）：用于安装依赖和运行命令。安装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 操作系统：Linux/MacOS/Windows（项目在 Linux 上测试）。

## 安装依赖

1. 克隆或进入项目目录：
   ```
   cd jobnova-crawler-demo
   ```

2. 使用 uv 同步依赖（安装所有依赖）：
   ```
   uv sync
   ```
   这会根据 `pyproject.toml` 安装 Scrapy 和其他库，如 beautifulsoup4、elasticsearch 等。

3. 安装 Playwright 浏览器（项目依赖 playwright 用于浏览器自动化）：
   ```
   uv run playwright install
   ```
   这会下载并安装 Chromium、Firefox 和 WebKit 浏览器，支持 headless 模式抓取。

## 运行抓取程序
### 项目中的3个例子：
基于json解析：`jobs/spiders/bs4_Apple.py` 
基于BeautifulSoup 解析：`jobs/spiders/bs4_Cisco.py`
基于playwright 解析：`jobs/spiders/pr_bloomberg.py`

### 基本命令

使用以下命令运行 Apple 职位爬虫：
```
uv run scrapy crawl Apple
or
uv run scrapy crawl "Apple"

```

- **解释**：
  - `uv run`：使用 uv 在虚拟环境中运行命令，确保依赖正确加载。
  - `scrapy crawl Apple`：启动名为 "Apple" 的爬虫（定义在 `jobs/spiders/bs4_Apple.py` 中）。
  
- **爬虫行为**：
  - 抓取 Apple 官网职位 API（https://jobs.apple.com/api/v1/search）。
  - 默认抓取前 6 页职位，按 "newest" 排序。
  - 过滤条件：
    - 仅处理最近 2 天内的职位。
    - 检查职位位置是否在 `jobs/locations.py` 定义的监控范围内。
    - 使用 `jobs/libabang.py` 中的 API 分析职位标题，获取标签 ID（如果无标签，跳过）。
  - 数据项（JobsItem）包括：公司名（"Apple"）、职位标题、链接、位置描述。
  - 通过 `SaveByApi` 管道（settings.py 中配置）保存数据，可能上传到外部 API 或数据库。

- **预期输出**：
  - 终端日志：显示抓取进度、职位位置、标签分析结果。
  - 数据保存：职位信息通过管道处理，可能输出到 Elasticsearch 或其他存储（取决于 API 配置）。
  - 示例日志：
    ```
    ------------ job_location: Austin, Texas, United States
    ```
  - 如果无符合职位，日志中可能显示跳过信息。

- **运行结果 
  - 正常会保存到目录 items 下对应的'[公司名].json' 文件**：
  - 对于能够获得 发布时间的岗位列表，需要加上判断 发布时间是否小于2天，我们只需要2天内发布的岗位，如下面的代码: 
  ![alt text](imgs/image.png)

### 其他运行选项

- 运行其他爬虫（如果有）：替换 "Apple" 为其他 spider 名，如 "pr_bloomberg"（如果实现）。
  ```
  uv run scrapy crawl pr_bloomberg
  ```

- 调试模式：添加 `-L DEBUG` 查看详细日志。
  ```
  uv run scrapy crawl Apple -L DEBUG
  ```

- 限制页数：在 spider 代码中修改 `self.page < 6`（当前硬编码为 6 页）。

## 配置说明

### Scrapy 设置（jobs/settings.py）

- **BOT_NAME**：'jobs'（项目名）。
- **SPIDER_MODULES**：'jobs.spiders'（爬虫位置）。
- **MIDDLEWARES**：
  - CrawlerSpiderMiddleware 和 JobsDownloaderMiddleware：自定义处理。
  - 禁用 MetaRefreshMiddleware：防止重定向循环。
- **PIPELINES**：
  - SaveByApi：处理并保存项（优先级 301）。
- **自定义配置**：
  - `ERR_INFOS`：错误信息映射，用于检测职位不可用（如 "no longer available"）。
  - `TAG_RATE_DATAS`：标签分类数据，用于 AI/数据科学/计算机等职位分类。

### 自定义模块
#### 代码中必须使用下面的两个函数。尽管现在返回的是固定值。
- `jobs/libabang.py`：API 类，用于分析职位（`self.api.analyze(item)`）。
- `jobs/locations.py`：位置检查（`Locations().if_in_monitor(job_location)`）。
- `jobs/items.py`：定义 JobsItem 字段。

要修改过滤或分析：
- 编辑 `bs4_Apple.py` 中的 `start_requests` 和 `parse` 方法。
- 更新 `locations.py` 添加监控位置。
- 配置 API 密钥（如果需要，在环境变量或 libabang.py 中）。

### 依赖管理

- 添加新依赖：编辑 `pyproject.toml` 的 `dependencies`，然后 `uv sync`。
- 锁定文件：`uv.lock` 自动生成，确保可重复安装。

## 新增岗位检测
### 实现步骤
- 分析获取岗位页面元素并决定使用哪种抓取方式： 
  ```
  基于json解析：`jobs/spiders/bs4_Apple.py` 
  基于BeautifulSoup 解析：`jobs/spiders/bs4_Cisco.py`
  基于playwright 解析：`jobs/spiders/pr_bloomberg.py`
  ```
- 按需求实现抓取代码
- 运行新增的岗位检测，如： 
  ```
  uv run scrapy crawl Apple
  ```
- items 目录下查看是否生成了对应的'[公司名].json' 文件

## 注意事项

- **合规性**：遵守 robots.txt（当前未启用 ROBOTSTXT_OBEY）。Apple API 可能有速率限制，建议添加 DOWNLOAD_DELAY（当前未设置）。
- **代理/头部**：spider 使用固定 HEADERS 模拟浏览器。如果被封禁，考虑添加代理（通过 middlewares）。
- **数据隐私**：抓取职位信息用于内部使用，避免滥用。
- **错误处理**：如果 API 分析失败（len(tagids) == 0），职位将被跳过。检查 ERR_INFOS 中的公司特定错误。
- **扩展**：要添加新 spider，运行 `scrapy genspider new_spider example.com`，然后置于 `jobs/spiders/`。
- **测试**：运行后检查日志，确保位置和标签正确。使用 `pdb.set_trace()`（代码中注释）调试。

## 故障排除

- **命令未找到**：确保 uv 已安装，并运行 `uv sync`。
- **依赖错误**：检查 Python 版本 >=3.12，重新 `uv sync`。
- **无数据**：验证网络连接，检查位置是否在监控列表，或放宽日期过滤（修改 timedelta(days=2)）。
- **API 失败**：检查 `libabang.py` 中的 API 配置，可能需要密钥。

更多 Scrapy 文档：https://docs.scrapy.org/en/latest/

如需帮助，参考项目文件或 Scrapy 社区。
