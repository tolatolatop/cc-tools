# clang-tidy wrap 最终总结案

## 1. 结论

建议采用一个基于 `clang-tidy` 的 Python CLI 工具，项目名保持 `clang-tidy-wrap`，CLI 名采用 `ctwrap`。项目使用 `uv`/`uvx` 管理与分发，定位不是“再包一层命令”，而是构建一个面向 agent 的、可解释的、可回退的静态分析基础设施。

最终推荐方案以 [`.codex/plans/clang-tidy-agent-wrap-design.md`](/home/vagrant/lsp-learn/cc-tools/.codex/plans/clang-tidy-agent-wrap-design.md) 为主线，吸收其他计划中的骨架和交付顺序，但拒绝不可靠的“伪 compile_commands”主路径和扫描阶段内置 AI 推理。

## 2. 工具定位

`ctwrap` 负责做四件事：

- 为 `clang-tidy` 提供工程化执行入口
- 为 Linux 内核和交叉编译场景补足运行上下文
- 在无编译数据库时提供显式降级扫描
- 为 agent 输出稳定、结构化、可排序、可追溯的结果

它不负责：

- 直接生成 LLM 风格结论
- 在扫描阶段做不可复现的“AI 修复建议”
- 伪造高可信编译上下文

## 3. 推荐技术路线

- 语言：Python `>=3.11`
- 包管理与执行：`uv` + `uvx`
- 构建后端：`hatchling`
- CLI：`typer`
- 配置模型：`pydantic` + `PyYAML`
- 输出：`orjson` + 文本摘要

推荐脚本入口：

```toml
[project.scripts]
ctwrap = "ctwrap.cli:app"
```

当前实现基线：

- 已完成 `db`
- 已完成 `doctor`
- 已完成 `print-cmd`
- 已完成 `report.json`
- 已完成基础 `agent-report.json`
- 已完成真实 `clang-tidy` 端到端测试

## 4. 三种核心模式

### 4.1 `db`

适用于已有 `compile_commands.json` 的工程。

特点：

- 结果可信度最高
- 作为 v1 首先落地
- 支持 compile DB 条目选择、flag 过滤、交叉参数注入

### 4.2 `kernel-auto-db`

适用于 Linux 内核源码树。

特点：

- 优先复用已有数据库
- 否则调用 `scripts/clang-tools/gen_compile_commands.py`
- 可选执行 `make olddefconfig prepare modules_prepare`
- 失败时可显式回退到 `fallback`

关键原则：

- 不以“自行解析 Makefile 后拼伪数据库”作为主路径
- 所有回退都必须被记录

### 4.3 `fallback`

适用于没有编译数据库的工程或局部文件。

特点：

- 基于 include、define、target、sysroot、toolchain 构建最小上下文
- 强制输出 `confidence`
- 强制输出 `confidence_reasons`
- 只作为最佳努力扫描，不伪装成精确模式

## 5. Linux 内核支持结论

Linux 内核支持必须围绕真实 Kbuild 产物设计，而不是围绕静态猜测设计。

最终建议：

- 优先识别内核树
- 优先使用内核自带 `gen_compile_commands.py`
- 数据库新鲜度至少考虑：
  - `compile_commands.json`
  - `.config`
  - `include/generated/`
  - `arch/*/include/generated/`
  - 待扫描文件
- 过滤内核特有且 clang 不接受的 GCC 参数
- 将原始 flags、过滤后 flags、过滤原因写入报告

## 6. 交叉编译支持结论

交叉编译支持必须显式建模，不能只依赖透传 `CROSS_COMPILE`。

最低需要支持：

- `ARCH`
- `CROSS_COMPILE`
- `--target`
- `--sysroot`
- `--gcc-toolchain`
- 额外系统头路径

参数优先级建议：

1. CLI
2. 配置文件
3. 环境变量
4. 从 `compile_commands.json` 推断

## 7. Agent 友好设计结论

这是该工具相对普通 wrapper 的核心差异。

最终要求：

- 输出通用 JSON
- 输出 agent 专用 JSON
- 输出文本摘要
- 每条 finding 都应尽量携带：
  - `confidence`
  - `context_kind`
  - `repro command`
  - `filtered_flags`
  - `build_origin`
  - `result_trust`

agent JSON 必须版本化：

- `agent_schema_version: 1`

并区分：

- required 字段
- optional 字段
- experimental 字段

## 8. 必须补齐的工程规则

### 8.1 同文件多条 compile DB 命令

不能默认取第一条。

需要稳定选择规则，至少考虑：

- CLI 显式 selector
- `directory` 接近度
- 条目完整性
- 目标架构一致性

并输出：

- `entry_selection_reason`
- `candidate_entry_count`

### 8.2 Header 变更处理

不能把 `.h` 当普通主翻译单元直接做强结论。

必须做 header 到 TU 的映射：

- 从 compile DB 反推候选 TU
- 可结合依赖文件或 include 关系
- 若无法可靠映射，则标记为 `advisory-only`

### 8.3 解析器版本门控

不同 `clang-tidy` 版本输出可能不同。

必须：

- 在 `doctor` 中检测版本
- 解析器按版本选择策略
- JSON 不稳定时回退到文本解析
- 把解析模式写入 `run_meta`

## 9. 输出与退出码建议

### 输出

- `report.json`：完整运行结果
- `agent-report.json`：agent 消费视图
- `report.txt`：人类摘要
- `report.sarif`：可选

### 退出码

- `0`：成功且未超阈值
- `1`：成功但发现超阈值问题
- `2`：环境或执行失败
- `3`：仅低置信降级结果，不适合作为严格 gate

## 10. 推荐 v1 范围

v1 不应过宽，建议收敛为：

1. `db` 模式
2. 统一报告模型
3. `doctor`
4. `print-cmd`
5. 基础 JSON/text 输出
6. 基础 `agent-report.json`

明确不放进 v1 核心闭环的内容：

- prompt view 花样输出
- 复杂 SARIF 扩展
- 深度缓存优化
- 大量 profile 变体

## 11. 推荐实施顺序

### Phase 1

- CLI 骨架
- 配置加载
- `db` 模式
- 统一 finding/report schema
- `doctor`
- `print-cmd`

### Phase 2

- Linux 内核识别
- `kernel-auto-db`
- 内核 flag 过滤
- 数据库新鲜度判断

### Phase 3

- `fallback`
- 交叉编译注入
- 置信度模型
- `result_trust`

### Phase 4

- `agent-report.json`
- finding 排序
- 建议动作生成
- schema 稳定化

### Phase 5

- 增量扫描
- 缓存
- 大仓库性能优化

## 12. 关键风险

- Linux 内核真实编译上下文复杂，误用伪数据库会导致系统性误报
- 无 compile DB 时很容易过度自信，必须显式降级
- 交叉编译工具链和 sysroot 缺失会显著降低结果质量
- agent 如果消费的不是“结构化事实”而是“扫描器自带推理”，后续会难以验证和维护

## 13. 最终建议

最终方案应坚持以下原则：

1. 真实上下文优先，显式降级其次。
2. 扫描事实和 AI 推理解耦。
3. 为 agent 设计输出，而不是只为终端设计输出。
4. 先把 `db + doctor + report model` 做稳，再扩展内核和 fallback。
5. 所有过滤、回退、歧义选择都必须可追溯。

如果按这个总结案执行，`ctwrap` 会更像一个可依赖的代码检查基础设施，而不是一个偶尔能跑通的脚本包装器。
