# clang-tidy wrap 详细落地计划

## 1. 实现目标

本计划用于把 `ctwrap` 从设计稿推进到可持续演进的工程实现。当前实现主线锁定为：

- Python + `uv`/`uvx`
- `db` 模式优先
- `doctor`
- `print-cmd`
- 统一 `report.json`
- `agent-report.json`
- 真实 `clang-tidy` 端到端测试

本计划不再讨论产品方向，而只定义实现步骤、模块职责、测试要求和交付顺序。

## 2. 当前基线

当前仓库已经具备：

- `pyproject.toml`
- `src/ctwrap/` 基础包结构
- compile DB 加载
- `scan` / `doctor` / `print-cmd`
- 基础报告模型
- 基础单元测试
- 本机真实 `clang-tidy` 可执行环境

## 3. 阶段划分

### Phase 1: v1 闭环

目标：

- `db` 模式可用
- `doctor` 可诊断环境
- `print-cmd` 可复现最终命令
- `scan` 可产出完整 JSON
- `agent-report.json` 可供 agent 消费
- 有真实 `clang-tidy` 端到端测试

交付物：

- CLI 命令
- 报告 schema
- 自动化测试
- 最小样例

### Phase 2: 质量收紧

目标：

- 更清晰的错误分类
- 更完整的 doctor 分级
- compile DB 多条 entry 选择理由
- 过滤参数记录
- 更稳定的退出码语义

交付物：

- 结构化运行错误
- 扫描失败/环境失败/规则命中三类退出码
- `print-cmd` 显示原始与最终命令差异

### Phase 3: 内核与交叉编译支撑

目标：

- Linux 内核目录识别
- compile DB 自动发现与复用
- `ARCH` / `target` / `sysroot` 注入
- 基础内核 doctor 检查

交付物：

- `kernel-auto-db` 只读探测
- toolchain 解析器
- flags 过滤规则

### Phase 4: 降级模式

目标：

- `fallback` 模式
- `confidence` 与 `result_trust`
- 建议动作生成

交付物：

- 降级上下文构造
- 低/中/高置信度计算
- 降级解释字段

## 4. 模块落地清单

### 4.1 `config`

文件：

- `src/ctwrap/config/schema.py`
- `src/ctwrap/config/loader.py`

职责：

- 配置 schema 定义
- YAML 加载
- CLI 覆盖配置

落地要求：

- 所有 CLI 参数都能覆盖配置
- 所有路径在进入执行层前完成规范化
- schema 允许后续平滑扩展

### 4.2 `compilation`

文件：

- `src/ctwrap/compilation/database.py`

职责：

- 加载 `compile_commands.json`
- 规范化路径
- 条目分组
- 文件到条目映射

落地要求：

- 支持 `arguments`
- 支持 `command`
- 支持 strip/add flags
- 对多条 entry 有稳定选择策略

### 4.3 `doctor`

文件：

- `src/ctwrap/doctor.py`

职责：

- 检查 `clang-tidy`
- 检查 `clang`
- 检查 compile DB
- 检查关键环境条件

落地要求：

- 输出 `ERROR/WARN/INFO`
- 版本信息可见
- 对缺失依赖给出明确结果

### 4.4 `scan`

文件：

- `src/ctwrap/scan.py`

职责：

- 组装最终命令
- 调用 `clang-tidy`
- 解析输出
- 汇总 findings

落地要求：

- 每文件独立执行
- 超时隔离
- 失败文件写入报告
- 每条 finding 附带 repro command

### 4.5 `report`

文件：

- `src/ctwrap/report/model.py`
- `src/ctwrap/report/render.py`

职责：

- 定义运行报告
- 定义 agent 报告
- 渲染 JSON/text

落地要求：

- `report.json` 为事实源
- `agent-report.json` 为派生视图
- schema 尽量稳定

### 4.6 `cli`

文件：

- `src/ctwrap/cli.py`

职责：

- 暴露命令
- 汇总输出
- 管理退出码

落地要求：

- `doctor`
- `print-cmd`
- `scan`
- 参数命名与设计文档保持一致

## 5. 文件级实施顺序

### 第一步

- 稳定 `pyproject.toml`
- 稳定 CLI 入口
- 稳定包导入

### 第二步

- 稳定 compile DB 加载
- 稳定 `print-cmd`
- 补充原始命令与最终命令输出

### 第三步

- 稳定 `scan`
- 稳定 regex/文本解析
- 报告中加入失败文件记录

### 第四步

- 稳定 `agent-report.json`
- 加入 `confidence` / `result_trust`
- 加入 `next_actions`

### 第五步

- 增加端到端测试
- 增加 golden report 基线
- 增加真实 `clang-tidy` 样例

## 6. 测试计划

### 6.1 单元测试

覆盖：

- compile DB 加载
- entry 选择
- 文本诊断解析
- report 渲染

### 6.2 集成测试

覆盖：

- `doctor`
- `print-cmd`
- `scan --json`
- `scan --agent-json`

### 6.3 真实端到端测试

环境要求：

- 系统存在 `clang-tidy`

样例要求：

- 一个可编译的最小 C++ 文件
- 一个稳定触发的 `clang-tidy` rule
- 一个最小 `compile_commands.json`

当前选定样例：

- 规则：`modernize-use-nullptr`
- 源码：`NULL` 改 `nullptr`

### 6.4 验收条件

满足以下条件才算 v1 闭环完成：

- `uv run ctwrap doctor` 正常输出
- `uv run ctwrap print-cmd ...` 正常输出
- `uv run ctwrap scan ...` 能稳定抓到真实 finding
- `report.json` 与 `agent-report.json` 可写出
- `pytest` 全通过

## 7. 端到端测试执行脚本

固定流程：

1. 安装依赖：`uv sync`
2. 确保 `clang-tidy` 可执行
3. 生成最小源码和 `compile_commands.json`
4. 执行 `uv run ctwrap doctor`
5. 执行 `uv run ctwrap print-cmd`
6. 执行 `uv run ctwrap scan --json ... --agent-json ...`
7. 断言输出文件存在且 findings 数符合预期

## 8. 代码生成约束

实现时必须遵守：

1. 不把伪 compile DB 当成高可信输入。
2. 不把 AI 推理写进扫描器。
3. `agent-report.json` 必须来自 `report.json` 派生。
4. 所有过滤、回退、失败都必须可追踪。
5. 所有真实行为都必须能通过自动化测试验证。

## 9. 当前之后的直接任务

以下任务按顺序执行：

1. 完善 `doctor` 分级和版本处理
2. 完善 `print-cmd` 的原始/最终命令输出
3. 完善 `scan` 的失败分类和退出码
4. 增加真实 `clang-tidy` 端到端测试
5. 固化 `report.json` 与 `agent-report.json` 的基线样例
