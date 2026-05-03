import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("astrbot_plugin_mysql_backup", "数据库备份", "MySQL数据库备份插件", "1.0.0")
class MySQLBackupPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.backup_dir = Path("./db_backups")
        self.backup_dir.mkdir(exist_ok=True)

    async def initialize(self):
        """插件初始化"""
        logger.info("MySQL 数据库备份插件已加载")

    @filter.command("db_backup")
    async def backup_database(self, event: AstrMessageEvent):
        """导出数据库为SQL文件并发送到聊天"""
        try:
            # 获取插件配置
            plugin_config = self.context.config
            
            if not plugin_config:
                yield event.plain_result("❌ 插件配置未找到，请检查配置文件")
                return
            
            db_host = plugin_config.get("db_host", "127.0.0.1")
            db_port = plugin_config.get("db_port", 3306)
            backup_databases = plugin_config.get("backup_databases", [])
            
            if not backup_databases:
                yield event.plain_result("❌ 未配置需要备份的数据库")
                return
            
            yield event.plain_result(
                f"🔄 开始备份数据库...\n数据库: {', '.join(backup_databases)}"
            )
            
            # 导出每个数据库
            for db_name in backup_databases:
                try:
                    await self.backup_single_database(
                        db_host, 
                        db_port, 
                        db_name
                    )
                except Exception as e:
                    yield event.plain_result(
                        f"⚠️ 备份数据库 {db_name} 失败: {str(e)}"
                    )
                    continue
            
            # 发送备份文件
            backup_files = list(self.backup_dir.glob("*.sql"))
            
            if not backup_files:
                yield event.plain_result("❌ 没有生成任何备份文件")
                return
            
            # 发送每个备份文件信息
            for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:  # 只显示最新5个
                try:
                    file_size = backup_file.stat().st_size
                    yield event.plain_result(
                        f"✅ {backup_file.name}\n"
                        f"📊 大小: {self.format_file_size(file_size)}\n"
                        f"📁 路径: {backup_file.absolute()}"
                    )
                except Exception as e:
                    yield event.plain_result(
                        f"⚠️ 处理备份文件 {backup_file.name} 失败: {str(e)}"
                    )
            
            yield event.plain_result(
                f"✨ 备份完成！共生成 {len(backup_files)} 个文件"
            )
            
        except Exception as e:
            logger.error(f"备份过程出错: {e}", exc_info=True)
            yield event.plain_result(f"❌ 备份过程出错: {str(e)}")

    @filter.command("db_help")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """🔧 MySQL 数据库备份插件使用指南

📌 命令:
  /db_backup - 备份配置中所有指定的数据库
  /db_help - 显示此帮助信息

🔧 配置文件说明 (_conf_schema.json):
  • db_host: 数据库地址 (默认: 127.0.0.1)
  • db_port: 数据库端口 (默认: 3306)
  • backup_databases: 需要备份的数据库列表

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
  4. 显示备份文件信息

⚠️ 注意:
  • 需要安装 MySQL 客户端 (包含mysqldump)
  • 需要数据库的访问权限
  • 备份文件存储在 ./db_backups 目录"""
        
        yield event.plain_result(help_text)

    async def backup_single_database(
        self,
        db_host: str,
        db_port: int,
        db_name: str
    ) -> None:
        """使用mysqldump导出单个数据库"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"{db_name}_{timestamp}.sql"
        
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
        
        logger.info(f"开始备份数据库 {db_name} 到 {backup_file}")
        
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
            logger.info(f"数据库 {db_name} 备份成功，文件大小: {self.format_file_size(file_size)}")
            
        except FileNotFoundError:
            raise RuntimeError(
                "找不到mysqldump命令。请确保已安装MySQL客户端:\n"
                "• Ubuntu/Debian: sudo apt-get install mysql-client\n"
                "• CentOS/RHEL: sudo yum install mysql\n"
                "• macOS: brew install mysql-client"
            )
        except Exception as e:
            if backup_file.exists():
                backup_file.unlink()
            raise

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f}TB"

    async def terminate(self):
        """插件卸载时调用"""
        logger.info("MySQL 数据库备份插件已卸载")

