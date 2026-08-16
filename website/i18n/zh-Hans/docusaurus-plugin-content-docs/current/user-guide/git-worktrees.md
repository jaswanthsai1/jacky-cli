---
sidebar_position: 3
sidebar_label: "Git Worktrees"
title: "Git Worktrees"
description: "使用 git worktrees 和隔离检出在同一仓库中安全运行多个 Jacky agent"
---

# Git Worktrees

Jacky Agent 常用于大型、长期维护的仓库。当你需要：

- 在同一项目中**并行运行多个 agent**，或
- 将实验性重构与主分支隔离，

Git **worktrees** 是为每个 agent 提供独立检出（checkout）而无需复制整个仓库的最安全方式。

本页介绍如何将 worktrees 与 Jacky 结合使用，使每个会话拥有干净、隔离的工作目录。

## 为什么在 Jacky 中使用 Worktrees？

Jacky 将**当前工作目录**视为项目根目录：

- CLI：运行 `jacky` 或 `jacky chat` 时所在的目录
- Messaging gateway：由 `MESSAGING_CWD` 设置的目录

如果在**同一检出**中运行多个 agent，它们的变更可能相互干扰：

- 一个 agent 可能删除或覆盖另一个正在使用的文件。
- 难以区分哪些变更属于哪个实验。

使用 worktrees 后，每个 agent 拥有：

- **独立的分支和工作目录**
- **独立的 Checkpoint Manager 历史**，用于 `/rollback`

另请参阅：[Checkpoints 与 /rollback](./checkpoints-and-rollback.md)。

## 快速开始：创建 Worktree

在主仓库（包含 `.git/` 的目录）中，为功能分支创建新的 worktree：

```bash
# 从主仓库根目录
cd /path/to/your/repo

# 在 ../repo-feature 中创建新分支和 worktree
git worktree add ../repo-feature feature/jacky-experiment
```

这将创建：

- 新目录：`../repo-feature`
- 新分支：`feature/jacky-experiment`，已在该目录中检出

现在可以 `cd` 进入新 worktree 并在其中运行 Jacky：

```bash
cd ../repo-feature

# 在 worktree 中启动 Jacky
jacky
```

Jacky 将：

- 将 `../repo-feature` 视为项目根目录。
- 使用该目录进行上下文文件读取、代码编辑和工具调用。
- 使用**独立的 checkpoint 历史**，`/rollback` 的作用范围限定在此 worktree。

## 并行运行多个 Agent

可以创建多个 worktree，每个对应独立的分支：

```bash
cd /path/to/your/repo

git worktree add ../repo-experiment-a feature/jacky-a
git worktree add ../repo-experiment-b feature/jacky-b
```

在不同终端中分别运行：

```bash
# 终端 1
cd ../repo-experiment-a
jacky

# 终端 2
cd ../repo-experiment-b
jacky
```

每个 Jacky 进程：

- 在各自的分支上工作（`feature/jacky-a` 与 `feature/jacky-b`）。
- 在不同的 shadow repo 哈希下写入 checkpoint（由 worktree 路径派生）。
- 可独立使用 `/rollback`，互不影响。

以下场景尤为适用：

- 批量重构。
- 对同一任务尝试不同方案。
- 将 CLI 与 gateway 会话配对，针对同一上游仓库运行。

## 安全清理 Worktrees

实验完成后：

1. 决定是否保留该工作成果。
2. 如需保留：
   - 按常规方式将分支合并到主分支。
3. 移除 worktree：

```bash
cd /path/to/your/repo

# 移除 worktree 目录及其引用
git worktree remove ../repo-feature
```

注意事项：

- `git worktree remove` 在 worktree 存在未提交变更时会拒绝移除，除非强制执行。
- 移除 worktree **不会**自动删除分支；可使用常规 `git branch` 命令决定是否删除分支。
- `~/.jacky/checkpoints/` 下的 Jacky checkpoint 数据在移除 worktree 时不会自动清理，但通常体积很小。

## 最佳实践

- **每个 Jacky 实验对应一个 worktree**
  - 为每项重要变更创建专用的分支/worktree。
  - 这样可保持 diff 聚焦，PR 小而易于审查。
- **以实验内容命名分支**
  - 例如：`feature/jacky-checkpoints-docs`、`feature/jacky-refactor-tests`。
- **频繁提交**
  - 使用 git commit 记录高层级里程碑。
  - 使用 [checkpoints 与 /rollback](./checkpoints-and-rollback.md) 作为工具驱动编辑之间的安全网。
- **使用 worktrees 时避免从裸仓库根目录运行 Jacky**
  - 优先使用 worktree 目录，使每个 agent 拥有明确的作用范围。

## 使用 `jacky -w`（自动 Worktree 模式）

Jacky 内置 `-w` 标志，可**自动创建一个一次性 git worktree** 及其独立分支。无需手动配置 worktree——只需 `cd` 进入仓库并运行：

```bash
cd /path/to/your/repo
jacky -w
```

Jacky 将：

- 在仓库内的 `.worktrees/` 下创建临时 worktree。
- 检出一个隔离分支（例如 `jacky/jacky-<hash>`）。
- 在该 worktree 内运行完整的 CLI 会话。

这是获得 worktree 隔离的最简便方式。也可与单次查询结合使用：

```bash
jacky -w -z "Fix issue #123"
```

如需并行运行多个 agent，在多个终端中分别运行 `jacky -w`——每次调用都会自动获得独立的 worktree 和分支。

## 综合运用

- 使用 **git worktrees** 为每个 Jacky 会话提供独立的干净检出。
- 使用**分支**记录实验的高层级历史。
- 使用 **checkpoints + `/rollback`** 在每个 worktree 内从错误中恢复。

这种组合带来：

- 强有力的保证，确保不同 agent 和实验互不干扰。
- 快速迭代周期，轻松从错误编辑中恢复。
- 干净、易于审查的 pull request。