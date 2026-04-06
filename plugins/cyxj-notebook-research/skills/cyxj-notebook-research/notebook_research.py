#!/usr/bin/env python3
"""Notebook LM 批量研究工具 — 提交视频 + 拉取研究结果"""

import json
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import frontmatter

# ── 常量 ──────────────────────────────────────────────
VAULT_BASE = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
)
TOPIC_DIR = VAULT_BASE / "灵感库" / "选题库"
REPORT_DIR = VAULT_BASE / "灵感库" / "研究报告"

# 匹配 YouTube URL（完整 URL 和 Video ID）
YOUTUBE_URL_PATTERN = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([0-9A-Za-z_-]{11}))"
)

# 源状态分类
SOURCE_STATUS_DONE = {"ready", "completed", "done", "indexed"}
SOURCE_STATUS_FAILED = {"failed", "error"}


# ── iCloud 幽灵文件处理 ───────────────────────────────

def ensure_file_downloaded(filepath: Path, max_wait: int = 10) -> bool:
    """确保 iCloud 文件已下载到本地，处理 .icloud 占位符。

    macOS 的"优化存储空间"会把不常用文件替换为占位符，
    例如 xxx.md 变为 .xxx.md.icloud。此函数检测并触发下载。

    返回 True 表示文件可用，False 表示等待超时。
    """
    # 如果文件直接存在，无需处理
    if filepath.exists() and not filepath.name.startswith("."):
        return True

    # 检查是否存在 .icloud 占位符
    icloud_name = f".{filepath.name}.icloud"
    icloud_path = filepath.parent / icloud_name

    if not icloud_path.exists():
        # 既没有原文件也没有占位符
        return filepath.exists()

    # 触发 iCloud 下载
    print(f"  检测到 iCloud 占位符，正在触发下载: {filepath.name}", file=sys.stderr)
    try:
        subprocess.run(
            ["brctl", "download", str(filepath)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        print(f"  警告：brctl download 调用失败（{e}）", file=sys.stderr)

    # 等待文件下载完成
    for i in range(max_wait):
        if filepath.exists() and not icloud_path.exists():
            print(f"  iCloud 文件已下载: {filepath.name}", file=sys.stderr)
            return True
        time.sleep(1)

    print(f"  警告：等待 {max_wait} 秒后文件仍未下载完成", file=sys.stderr)
    return filepath.exists()


# ── Frontmatter 工具函数（使用 python-frontmatter）────

def load_topic_file(filepath: Path) -> frontmatter.Post:
    """读取选题文件，返回 frontmatter.Post 对象"""
    return frontmatter.load(str(filepath))


def save_topic_file(filepath: Path, post: frontmatter.Post):
    """将 frontmatter.Post 对象写回文件"""
    frontmatter.dump(post, str(filepath))


# ── CLI 调用工具函数 ──────────────────────────────────

def run_notebooklm(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """调用 notebooklm CLI，返回结果。

    当捕获到认证错误（401/403）或连接超时时，在 stderr 中提示
    notebooklm-py 可能已失效。
    """
    cmd = ["notebooklm"] + args
    print(f"  执行: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"  超时：命令执行超过 {timeout} 秒", file=sys.stderr)
        print(
            "  提示：notebooklm-py 可能已失效，请检查是否需要更新"
            "（pip install --upgrade notebooklm-py）"
            "或重新登录（notebooklm login）",
            file=sys.stderr,
        )
        raise

    if result.returncode != 0:
        print(f"  错误 (exit {result.returncode}):", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        if result.stdout:
            print(f"  stdout: {result.stdout.strip()}", file=sys.stderr)

        # 检查是否为认证或连接错误
        combined_output = (result.stderr + result.stdout).lower()
        if any(kw in combined_output for kw in ("401", "403", "unauthorized", "forbidden", "timeout", "connection")):
            print(
                "  提示：notebooklm-py 可能已失效，请检查是否需要更新"
                "（pip install --upgrade notebooklm-py）"
                "或重新登录（notebooklm login）",
                file=sys.stderr,
            )

    return result


def extract_notebook_id(output: str) -> str | None:
    """从 notebooklm create 的输出中提取 notebook_id"""
    # 尝试多种可能的输出格式
    # 格式 1: 直接是 UUID
    uuid_pattern = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)
    match = uuid_pattern.search(output)
    if match:
        return match.group(1)
    # 格式 2: 纯字母数字 ID
    id_pattern = re.compile(r"(?:id|ID|notebook)[:\s]+([A-Za-z0-9_-]{8,})")
    match = id_pattern.search(output)
    if match:
        return match.group(1)
    # 格式 3: 整行就是 ID（去除空白）
    stripped = output.strip()
    if stripped and "\n" not in stripped and len(stripped) < 100:
        return stripped
    return None


def extract_source_info(output: str) -> list[dict]:
    """从 notebooklm source list 的输出中提取源信息

    返回: [{"id": "source_id", "title": "...", "status": "..."}, ...]
    """
    sources = []
    # 尝试解析为 JSON
    try:
        data = json.loads(output)
        # notebooklm source list --json 格式: {"sources": [...]}
        if isinstance(data, dict) and "sources" in data:
            return data["sources"]
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # 回退: 按行解析，寻找 ID 和状态信息
    lines = output.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        source = {}
        # 寻找 source ID
        id_match = re.search(r"(?:id|ID)[:\s]+([A-Za-z0-9_-]+)", line)
        if id_match:
            source["id"] = id_match.group(1)
        # 寻找状态
        status_match = re.search(r"(?:status|state)[:\s]+(\w+)", line, re.IGNORECASE)
        if status_match:
            source["status"] = status_match.group(1).lower()
        if source.get("id"):
            sources.append(source)

    return sources


def classify_sources(sources: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """将源按状态分为三类：完成、失败、处理中。

    返回: (done_sources, failed_sources, pending_sources)
    """
    done = []
    failed = []
    pending = []
    for s in sources:
        status = s.get("status", "").lower()
        if status in SOURCE_STATUS_DONE:
            done.append(s)
        elif status in SOURCE_STATUS_FAILED:
            failed.append(s)
        else:
            pending.append(s)
    return done, failed, pending


# ── 核心流程 ──────────────────────────────────────────

def cmd_submit(topic_file: Path):
    """第一步：提交视频到 Notebook LM"""
    # 0. 确保 iCloud 文件已下载
    if not ensure_file_downloaded(topic_file):
        print(f"错误：无法获取文件 {topic_file.name}（可能是 iCloud 未下载）", file=sys.stderr)
        sys.exit(1)

    # 1. 读取选题文件
    try:
        post = load_topic_file(topic_file)
    except Exception as e:
        print(f"错误：无法读取文件 {topic_file.name}（{e}）", file=sys.stderr)
        sys.exit(1)

    # 2. 确认 status
    status = post.metadata.get("status", "")
    if status != "未处理":
        print(f"错误：选题文件状态为「{status}」，不是「未处理」。", file=sys.stderr)
        if status == "研究中":
            print("提示：该话题已提交过，请用 fetch 子命令拉取结果。", file=sys.stderr)
        elif status == "异常":
            print("提示：该话题之前处理异常，可检查 error 字段了解原因。如需重试，请将 status 改回「未处理」。", file=sys.stderr)
        sys.exit(1)

    # 3. 提取 YouTube 链接
    content_text = post.content
    matches = YOUTUBE_URL_PATTERN.findall(content_text)
    if not matches:
        print("错误：选题文件中未找到 YouTube 链接。", file=sys.stderr)
        sys.exit(1)

    urls = [m[0] for m in matches]
    video_ids = [m[1] for m in matches]
    print(f"找到 {len(urls)} 个 YouTube 视频", file=sys.stderr)

    # 4. 创建 Notebook LM 笔记本
    topic_name = topic_file.stem
    result = run_notebooklm(["create", topic_name], timeout=30)
    if result.returncode != 0:
        print("错误：创建笔记本失败。", file=sys.stderr)
        sys.exit(1)

    notebook_id = extract_notebook_id(result.stdout)
    if not notebook_id:
        print(f"错误：无法从输出中提取 notebook_id。\n输出: {result.stdout}", file=sys.stderr)
        sys.exit(1)
    print(f"笔记本已创建: {notebook_id}", file=sys.stderr)

    # 5. 设置当前笔记本
    result = run_notebooklm(["use", notebook_id], timeout=15)
    if result.returncode != 0:
        print("警告：设置当前笔记本可能失败，继续尝试添加源...", file=sys.stderr)

    # 6. 逐个添加视频为源
    success_count = 0
    fail_count = 0
    for i, url in enumerate(urls):
        print(f"  添加视频 {i+1}/{len(urls)}: {video_ids[i]}", file=sys.stderr)
        result = run_notebooklm(["source", "add", url], timeout=60)
        if result.returncode == 0:
            success_count += 1
        else:
            fail_count += 1
            print(f"  警告：视频 {video_ids[i]} 添加失败", file=sys.stderr)

    if success_count == 0:
        print("错误：所有视频都添加失败。", file=sys.stderr)
        # 标记为异常状态
        post.metadata["status"] = "异常"
        post.metadata["notebook_id"] = notebook_id
        post.metadata["error"] = "所有视频添加到 Notebook LM 失败"
        save_topic_file(topic_file, post)
        sys.exit(1)

    # 7. 更新选题文件
    post.metadata["status"] = "研究中"
    post.metadata["notebook_id"] = notebook_id
    save_topic_file(topic_file, post)

    # 8. 输出摘要
    summary = {
        "action": "submit",
        "topic": topic_name,
        "notebook_id": notebook_id,
        "videos_total": len(urls),
        "videos_added": success_count,
        "videos_failed": fail_count,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_fetch(topic_file: Path):
    """第二步：拉取研究结果"""
    # 0. 确保 iCloud 文件已下载
    if not ensure_file_downloaded(topic_file):
        print(f"错误：无法获取文件 {topic_file.name}（可能是 iCloud 未下载）", file=sys.stderr)
        sys.exit(1)

    # 1. 读取选题文件
    try:
        post = load_topic_file(topic_file)
    except Exception as e:
        print(f"错误：无法读取文件 {topic_file.name}（{e}）", file=sys.stderr)
        sys.exit(1)

    # 2. 解析 frontmatter
    status = post.metadata.get("status", "")
    notebook_id = post.metadata.get("notebook_id", "")

    if status != "研究中":
        print(f"错误：选题文件状态为「{status}」，不是「研究中」。", file=sys.stderr)
        sys.exit(1)
    if not notebook_id:
        # notebook_id 丢失，标记为异常
        print("错误：选题文件中没有 notebook_id。", file=sys.stderr)
        post.metadata["status"] = "异常"
        post.metadata["error"] = "notebook_id 丢失，无法拉取结果"
        save_topic_file(topic_file, post)
        sys.exit(1)

    topic_name = topic_file.stem

    # 3. 设置当前笔记本
    result = run_notebooklm(["use", notebook_id], timeout=15)
    if result.returncode != 0:
        print("错误：无法设置笔记本。", file=sys.stderr)
        sys.exit(1)

    # 4. 检查源索引状态
    result = run_notebooklm(["source", "list", "--json"], timeout=30)
    if result.returncode != 0:
        print("错误：无法获取源列表。", file=sys.stderr)
        sys.exit(1)

    sources = extract_source_info(result.stdout)
    if not sources:
        print("错误：笔记本中没有找到源，或无法解析源列表。", file=sys.stderr)
        print(f"原始输出:\n{result.stdout}", file=sys.stderr)
        post.metadata["status"] = "异常"
        post.metadata["error"] = "笔记本中没有找到源"
        save_topic_file(topic_file, post)
        sys.exit(1)

    # 将源分为三类：完成、失败、处理中
    done_sources, failed_sources, pending_sources = classify_sources(sources)

    # 记录失败的源
    if failed_sources:
        failed_names = [s.get("title", s.get("id", "?")) for s in failed_sources]
        print(f"  警告：{len(failed_sources)} 个源解析失败，将跳过: {', '.join(failed_names)}", file=sys.stderr)

    # 如果有处理中的源，提示稍后再试
    if pending_sources:
        pending_count = len(pending_sources)
        print(f"还有 {pending_count} 个源正在索引中，请稍后再试。", file=sys.stderr)
        if failed_sources:
            print(f"（另有 {len(failed_sources)} 个源已失败，将在最终结果中跳过）", file=sys.stderr)
        print(json.dumps({
            "action": "fetch",
            "status": "pending",
            "pending_count": pending_count,
            "failed_count": len(failed_sources),
        }, ensure_ascii=False))
        sys.exit(2)

    # 如果所有源都失败，标记为异常
    if not done_sources:
        print("错误：所有视频源都解析失败，没有可用的转录内容。", file=sys.stderr)
        post.metadata["status"] = "异常"
        post.metadata["error"] = "所有视频源解析失败"
        save_topic_file(topic_file, post)
        summary = {
            "action": "fetch",
            "status": "error",
            "topic": topic_name,
            "error": "所有视频源解析失败",
            "failed_count": len(failed_sources),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(f"{len(done_sources)} 个源已索引完成，开始生成报告...", file=sys.stderr)

    # 5. 生成综合报告（异步：触发 → 轮询 → 下载）
    print("  触发综合报告生成...", file=sys.stderr)
    result = run_notebooklm(["generate", "report", "--format", "briefing-doc"], timeout=300)
    briefing = ""

    # 从输出中提取任务 ID
    task_id = None
    if result.returncode == 0 and result.stdout.strip():
        output = result.stdout.strip()
        # 检查是否为异步任务 ID（格式: "Started: <uuid>"）
        started_match = re.search(r"Started:\s*([0-9a-f-]{36})", output, re.IGNORECASE)
        if started_match:
            task_id = started_match.group(1)
        else:
            # 如果直接返回了内容（非异步），直接使用
            briefing = output

    if task_id:
        # 轮询等待报告生成完成
        print(f"  报告生成中（任务 {task_id[:8]}...），等待完成...", file=sys.stderr)
        max_polls = 30  # 最多等 5 分钟（30 × 10 秒）
        for attempt in range(max_polls):
            time.sleep(10)
            poll_result = run_notebooklm(["artifact", "poll", task_id], timeout=30)
            if poll_result.returncode == 0 and "completed" in poll_result.stdout.lower():
                print("  报告生成完成", file=sys.stderr)
                break
            if poll_result.returncode != 0 or "failed" in poll_result.stdout.lower():
                print("  警告：报告生成失败", file=sys.stderr)
                break
        else:
            print("  警告：报告生成超时（5 分钟）", file=sys.stderr)

        # 下载报告内容
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as tmp:
            tmp_path = tmp.name
        dl_result = run_notebooklm(
            ["download", "report", "-a", task_id, "--force", tmp_path], timeout=60
        )
        if dl_result.returncode == 0:
            try:
                briefing = Path(tmp_path).read_text(encoding="utf-8").strip()
                print(f"  报告已下载（{len(briefing)} 字符）", file=sys.stderr)
            except Exception:
                print("  警告：无法读取下载的报告文件", file=sys.stderr)
        else:
            print("  警告：报告下载失败", file=sys.stderr)
        # 清理临时文件
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    if not briefing:
        briefing = "（综合报告生成失败）"

    # 6. 写入研究报告文件
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"{topic_name}.md"

    today = date.today().isoformat()
    # 收集视频来源信息
    source_lines = []
    for source in done_sources:
        source_title = source.get("title", source.get("id", "未知"))
        source_lines.append(f"- {source_title}")

    report_lines = [
        "---",
        "source: ai-research",
        f"created: {today}",
        f'topic_file: "[[{topic_name}]]"',
        f"notebook_id: {notebook_id}",
        "---",
        "",
        "## 视频来源",
        "",
    ]
    report_lines.extend(source_lines)
    report_lines.append("")

    # 标注失败的源
    if failed_sources:
        report_lines.append("### 以下视频源解析失败（已跳过）")
        report_lines.append("")
        for s in failed_sources:
            name = s.get("title", s.get("id", "未知"))
            report_lines.append(f"- {name}（状态: {s.get('status', '未知')}）")
        report_lines.append("")

    report_lines.append("---")
    report_lines.append("")
    report_lines.append(briefing)
    report_lines.append("")

    report_content = "\n".join(report_lines)
    report_file.write_text(report_content, encoding="utf-8")
    print(f"研究报告已写入: {report_file.name}", file=sys.stderr)

    # 8. 更新选题文件状态
    post.metadata["status"] = "已完成"
    # 清除可能残留的 error 字段
    post.metadata.pop("error", None)
    save_topic_file(topic_file, post)

    # 9. 输出摘要
    summary = {
        "action": "fetch",
        "status": "completed",
        "topic": topic_name,
        "sources_count": len(done_sources),
        "failed_sources_count": len(failed_sources),
        "report_file": str(report_file),
        "has_briefing": briefing != "（综合报告生成失败）",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


# ── 入口 ──────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("用法: notebook_research.py <submit|fetch> <选题文件路径>", file=sys.stderr)
        print("  submit  — 提交视频到 Notebook LM（status: 未处理 → 研究中）", file=sys.stderr)
        print("  fetch   — 拉取研究结果（status: 研究中 → 已完成/异常）", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    topic_path = Path(sys.argv[2])

    # 确保文件可用（处理 iCloud 占位符）
    if not ensure_file_downloaded(topic_path):
        print(f"错误：文件不存在或无法下载 {topic_path}", file=sys.stderr)
        sys.exit(1)

    if command == "submit":
        cmd_submit(topic_path)
    elif command == "fetch":
        cmd_fetch(topic_path)
    else:
        print(f"错误：未知子命令「{command}」，请使用 submit 或 fetch", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
