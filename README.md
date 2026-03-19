# clang-tidy-wrap

`ctwrap` 是一个面向 agent 代码检查场景的 `clang-tidy` 包装器。

当前已经实现的能力：

- 基于 `compile_commands.json` 的扫描
- 环境检查：`doctor`
- 命令复现：`print-cmd`
- 统一事实报告：`report.json`
- agent 视图报告：`agent-report.json`
- 文本摘要输出

默认检查规则：

- `-*,bugprone-*,clang-analyzer-*`

## 环境要求

- Python `>= 3.11`
- `uv`
- `clang`
- `clang-tidy`

本仓库当前已在 Ubuntu 22.04 + `clang-tidy-15` 上验证通过。

## 安装依赖

```bash
uv sync
```

如果系统里没有 `clang-tidy`，需要先安装，例如：

```bash
sudo apt-get update
sudo apt-get install -y clang-15 clang-tidy-15
sudo ln -sf /usr/bin/clang-tidy-15 /usr/local/bin/clang-tidy
```

## 命令概览

```bash
uv run ctwrap doctor
uv run ctwrap print-cmd path/to/file.c --compile-db build/compile_commands.json
uv run ctwrap scan path/to/file.c --compile-db build/compile_commands.json
```

## doctor

检查当前环境是否满足扫描条件。

```bash
uv run ctwrap doctor
uv run ctwrap doctor --compile-db build/compile_commands.json
```

输出包含：

- `clang-tidy` 是否存在
- `clang` 是否存在
- `clang-tidy` 版本
- `compile_commands.json` 是否可读

## print-cmd

打印某个文件最终会执行的 `clang-tidy` 命令。

```bash
uv run ctwrap print-cmd src/foo.cpp --compile-db build/compile_commands.json
```

输出内容包括：

- 原始 compile DB 命令
- 被过滤的 flags
- 最终执行命令

## 单文件扫描

这是当前最直接的单文件扫描命令：

```bash
uv run ctwrap scan src/foo.cpp --compile-db build/compile_commands.json
```

不传 `--checks` 时，默认使用：

```text
-*,bugprone-*,clang-analyzer-*
```

带检查规则的单文件扫描：

```bash
uv run ctwrap scan src/foo.cpp \
  --compile-db build/compile_commands.json \
  --checks=-*,modernize-use-nullptr
```

同时写出报告文件：

```bash
uv run ctwrap scan src/foo.cpp \
  --compile-db build/compile_commands.json \
  --checks=-*,modernize-use-nullptr \
  --json report.json \
  --agent-json agent-report.json \
  --text report.txt
```

退出码语义：

- `0`：没有 finding
- `1`：扫描成功，但发现了 warning/error
- `2`：扫描执行失败或文件级失败

## 输出文件

### `report.json`

事实源报告，包含：

- `run_meta`
- `summary`
- `findings`
- `errors`
- `next_actions`

### `agent-report.json`

为 agent 消费准备的派生视图，包含：

- `agent_schema_version`
- `summary`
- `trust_summary`
- `actionable_findings`
- `next_actions`

### `report.txt`

适合终端和日志查看的摘要。

## 最小可运行示例

```bash
mkdir -p .demo
cat > .demo/test.cpp <<'EOF'
#include <cstddef>
int *p = NULL;
int main() { return p == NULL; }
EOF

cat > .demo/compile_commands.json <<'EOF'
[
  {
    "directory": "/absolute/path/to/.demo",
    "file": "test.cpp",
    "arguments": ["clang++", "-std=c++17", "-c", "test.cpp"]
  }
]
EOF

uv run ctwrap scan .demo/test.cpp \
  --compile-db .demo/compile_commands.json \
  --checks=-*,modernize-use-nullptr \
  --json .demo/report.json \
  --agent-json .demo/agent-report.json \
  --text .demo/report.txt
```

## 测试

运行全部测试：

```bash
uv run pytest -q
```

当前测试包含：

- compile DB 加载测试
- 诊断解析测试
- CLI 端到端测试
- 真实 `clang-tidy` 扫描测试
