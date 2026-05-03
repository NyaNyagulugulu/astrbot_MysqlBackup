import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

from astrbot.api.v1 import plugin, AstrMessageEvent, MessageChain
from astrbot.api.v1.config import AstrBotConfig


@plugin.on_command(
    command="db_backup",
    description="导出配置中的数据库为SQL备份文件",
)
async def backup_database(event: AstrMessageEvent, **kwargs):
    """
    导出数据库为SQL文件并发送到聊天
    使用方式: /db_backup 或 !db_backup
    """
    try:
        # 获取插件配置
        plugin_config = event.bot.config.plugin_config.get("astrbot_plugin_mysql_backup", {})
        
        if not plugin_config:
            await event.send_message(
                MessageChain([
                    "❌ 插件配置未找到，请检查配置文件"
                ])
            )
            return
        
        db_host = plugin_config.get("db_host", "127.0.0.1")
        db_port = plugin_config.get("db_port", 3306)
        backup_databases = plugin_config.get("backup_databases", [])
        
        if not backup_databases:
            await event.send_message(
                MessageChain([
                    "❌ 未配置需要备份的数据库"
                ])
            )
            return
        
        await event.send_message(
            MessageChain([
                f"🔄 开始备份数据库...\n数据库: {', '.join(backup_databases)}"
            ])
        )
        
        # 创建备份目录
        backup_dir = Path("./db_backups")
        backup_dir.mkdir(exist_ok=True)
        
        # 导出每个数据库
        for db_name in backup_databases:
            try:
                await backup_single_database(
                    db_host, 
                    db_port, 
                    db_name, 
                    backup_dir
                )
            except Exception as e:
                await event.send_message(
                    MessageChain([
                        f"⚠️ 备份数据库 {db_name} 失败: {str(e)}"
                    ])
                )
                continue
        
        # 发送备份文件
        backup_files = list(backup_dir.glob("*.sql"))
        
        if not backup_files:
            await event.send_message(
                MessageChain([
                    "❌ 没有生成任何备份文件"
                ])
            )
            return
        
        # 发送每个备份文件
        for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                # 检查文件大小
                file_size = backup_file.stat().st_size
                if file_size > 100 * 1024 * 1024:  # 超过100MB
                    await event.send_message(
                        MessageChain([
                            f"⚠️ 文件 {backup_file.name} 过大 ({format_file_size(file_size)})，无法直接发送\n"
                            f"📁 文件路径: {backup_file.absolute()}"
                        ])
                    )
                    continue
                
                # 发送文件
                await event.send_message(
                    MessageChain([
                        f"✅ 备份完成: {backup_file.name}\n"
                        f"📊 文件大小: {format_file_size(file_size)}"
                    ])
                )
                
                # 尝试发送文件内容（如果是较小的文件）
                if file_size < 5 * 1024 * 1024:  # 小于5MB才尝试直接发送
                    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # 只读前1000字符预览
                        if len(content) < 200:
                            await event.send_message(
                                MessageChain([
                                    f"📄 {backup_file.name} 内容预览:\n```\n{content}\n```"
                                ])
                            )
                
            except Exception as e:
                await event.send_message(
                    MessageChain([
                        f"⚠️ 发送备份文件 {backup_file.name} 失败: {str(e)}"
                    ])
                )
        
        await event.send_message(
            MessageChain([
                f"✨ 所有数据库备份完成！共 {len(backup_files)} 个文件"
            ])
        )
        
    except Exception as e:
        await event.send_message(
            MessageChain([
                f"❌ 备份过程出错: {str(e)}"
            ])
        )


async def backup_single_database(
    db_host: str,
    db_port: int,
    db_name: str,
    backup_dir: Path
) -> None:
    """
    使用mysqldump导出单个数据库
    
    Args:
        db_host: 数据库主机
        db_port: 数据库端口
        db_name: 数据库名
        backup_dir: 备份目录
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"{db_name}_{timestamp}.sql"
    
    # 构建mysqldump命令
    cmd = [
        "mysqldump",
        "-h", db_host,
        "-P", str(db_port),
        "--single-transaction",
        "--quick",
        "--lock-tables=false",
        db_name
    ]
    
    try:
        # 运行mysqldump命令
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024*1024*50  # 50MB缓冲区
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"mysqldump命令执行失败: {error_msg}")
        
        # 写入文件
        with open(backup_file, 'wb') as f:
            f.write(stdout)
        
        file_size = backup_file.stat().st_size
        
    except FileNotFoundError:
        raise RuntimeError(
            "找不到mysqldump命令。\n"
            "请确保已安装MySQL客户端:\n"
            "- Ubuntu/Debian: sudo apt-get install mysql-client\n"
            "- CentOS/RHEL: sudo yum install mysql\n"
            "- macOS: brew install mysql-client"
        )
    except Exception as e:
        if backup_file.exists():
            backup_file.unlink()
        raise


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f}TB"


@plugin.on_command(
    command="db_help",
    description="显示数据库备份帮助信息",
)
async def show_help(event: AstrMessageEvent, **kwargs):
    """显示帮助信息"""
    help_text = """
🔧 MySQL 数据库备份插件使用指南

📌 命令:
  /db_backup  或  !db_backup
    - 备份配置中所有指定的数据库
    - 自动生成SQL文件并保存到 ./db_backups 目录

🔧 配置文件 (_conf_schema.json):
  - db_host: 数据库地址 (默认: 127.0.0.1)
  - db_port: 数据库端口 (默认: 3306)
  - backup_databases: 需要备份的数据库列表

💡 示例配置:
  {
    "db_host": "127.0.0.1",
    "db_port": 3306,
    "backup_databases": ["neko_music", "test_db"]
  }

📋 工作原理:
  1. 读取配置文件中的数据库信息
  2. 使用 mysqldump 命令导出数据库
  3. 生成时间戳的SQL文件
  4. 将备份文件信息发送到对话

⚠️ 注意:
  - 需要安装 MySQL 客户端 (包含mysqldump)
  - 需要数据库的访问权限
  - 大文件可能无法直接发送，会显示文件路径
"""
    await event.send_message(MessageChain([help_text]))
