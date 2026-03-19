# 对最终总结案的修订版评审清单

源文档：[`plans/clang-tidy-wrap-final-summary.md`](/home/vagrant/lsp-learn/cc-tools/plans/clang-tidy-wrap-final-summary.md)

这份文档不再只保留“提问”，而是把评审意见收敛为三类：

- 已建议锁定的默认决策
- 仍需在实现前明确的开放项
- 应写回主方案的补充条款

## 1. 建议直接锁定的默认决策

### 1.1 v1 范围

建议锁定为：

- `db` 模式
- `doctor`
- `print-cmd`
- 统一 `report.json`
- 基础 `agent-report.json`

说明：

- 不建议把 `kernel-auto-db` 放入 v1 闭环，否则交付风险明显上升
- `baseline new-only` 建议进入 v1.1，而不是阻塞 v1

### 1.2 clang-tidy 版本策略

建议：

- 最低支持版本固定为 `>=15`
- CI 固定一个主版本，例如 `15`
- 其他版本只作为兼容测试，不作为主发布基线

说明：

- 这样可以显著降低解析器门控和 golden report 漂移成本

### 1.3 AI 边界

建议明确写死：

- 扫描阶段不引入 LLM 推理
- 建议动作必须是规则化、可复现的
- 不输出“AI 修复结论”

说明：

- 工具输出的是扫描事实和上下文，不是推理结论

### 1.4 `kernel-auto-db` 默认回退策略

建议默认行为：

- 默认不静默回退
- `kernel-auto-db` 失败时返回错误，并在 CLI 上提供显式参数允许回退到 `fallback`

推荐 CLI 语义：

- `--allow-fallback`
- `--fallback-on kernel-db-failure`

说明：

- 对内核项目而言，静默降级很容易制造“看起来能跑、实际不可信”的结果

### 1.5 `fallback` 与 gate 关系

建议：

- `fallback` 结果默认是 `advisory`
- 仅当用户显式启用时，才允许低置信或纯 fallback 结果参与阻断
- exit code `3` 保留，用于“运行成功但不适合作为严格 gate”

## 2. 仍需在实现前确认的开放项

这些问题不适合继续模糊，应在开始编码前给出明确默认值。

### 2.1 compile DB 多条 entry 选择规则

当前需要补充为明确算法，而不是只列候选维度。

建议顺序：

1. CLI 显式 selector
2. 与扫描文件路径最接近的 `directory`
3. 与 `ARCH`/`target` 一致的条目
4. flags 更完整的条目
5. 若仍冲突，进入 `strict skip` 或 `best-effort demote-confidence`

### 2.2 `print-cmd` 输出内容

建议同时输出两份：

- 原始 compile DB 命令
- 过滤和注入后的最终执行命令

并附带：

- 被过滤的 flags
- 注入的 flags
- 选择该条目和该模式的原因

### 2.3 Header 到 TU 的映射失败行为

建议：

- 默认不阻断
- 在报告中标记为 `advisory-only`
- 输出 `mapping_confidence` 和 `mapping_reason`

原因：

- 头文件变更无法可靠映射到 TU 时，不应给出强结论

### 2.4 `ARCH` 与 `--target` 冲突

建议默认策略：

- 视为配置冲突
- `doctor` 报 `ERROR`
- `scan` 默认失败退出
- 提供显式参数允许“以 CLI 为准”

### 2.5 compile DB 推断优先级

当前总结案把“从 compile DB 推断”放在最后，建议补充说明：

- 对“补全缺省字段”时放最后
- 对“文件级真实编译上下文”时，compile DB 应优先于环境推断

否则语义容易被误读。

## 3. 应补写回主方案的条款

### 3.1 `agent-report.json` 与 `report.json` 的关系

建议明确为：

- 同源模型
- 两个视图
- 不维护两套彼此独立的 finding schema

推荐做法：

- `report.json` 为全量事实源
- `agent-report.json` 为筛选、排序、压缩后的 agent 视图

### 3.2 `confidence` 与 `result_trust` 的区别

建议在主方案中写清：

- `confidence`：描述扫描上下文是否完整
- `result_trust`：描述该 finding 是否适合参与阻断和强结论

推荐映射：

- `high confidence` 不必然等于 `strict`
- 但 `low confidence` 通常只能是 `advisory`

### 3.3 `filtered_flags` 的记录粒度

建议默认：

- run 粒度记录完整过滤清单
- finding 粒度只记录与该文件/该任务相关的过滤摘要

说明：

- 如果每个 finding 都展开完整 flags，会显著放大报告体积

### 3.4 `doctor` 检查分级

建议分为：

- `ERROR`：阻止高可信扫描
- `WARN`：结果可能降级
- `INFO`：辅助信息

最少检查项建议包括：

- `clang-tidy` 是否存在
- `clang` 是否存在
- 版本是否满足最低要求
- `compile_commands.json` 是否可读
- `sysroot` 是否存在
- 内核生成头是否存在

### 3.5 资源控制

建议在主方案中补一条：

- 默认并发数不只受 CPU 限制，还应受内存上限约束

否则大仓库下容易 OOM。

## 4. 测试补充建议

### 4.1 最小回归仓库

建议至少准备 3 套 fixtures：

- 普通 C 项目，带 compile DB
- 交叉编译样例，带 sysroot
- 精简内核样例或内核目录结构模拟

### 4.2 golden report

建议：

- 对 `report.json`
- 对 `agent-report.json`

都做 golden 对比测试，防止 schema 漂移。

### 4.3 fallback 稳定性测试

建议专门验证：

- 同一输入多次运行结果稳定
- 缺失 sysroot 时置信度正确下降
- 无法映射 header 时不会错误升级为 `strict`

## 5. 推荐优先决议的 5 个点

开始编码前，建议先把以下 5 项写成明确决策：

1. v1 范围是否锁定为 `db + doctor + print-cmd + report + agent-report`
2. clang-tidy 最低支持版本与 CI 固定版本
3. `kernel-auto-db` 默认是否禁止静默回退
4. `fallback` 的 gate/退出码语义
5. `agent-report.json` 的 required 字段与兼容策略

## 6. 总体判断

最终总结案的方向已经基本正确，尤其是：

- 拒绝伪 compile DB 主路径
- 强调显式降级
- 强调 agent 友好输出
- 强调事实层与 AI 层解耦

目前最需要补的不是更多功能点，而是把几个关键默认行为写死，避免实现阶段再次出现歧义：

- 默认是否自动回退
- 哪些结果可以阻断
- 多条 entry 如何裁决
- header 变更如何处理
- 两类 JSON 报告如何保持同源
