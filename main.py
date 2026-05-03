import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import * 

@register("astrbot_plugin_mysql_backup", "数据库备份", "MySQL数据库直接发送备份插件", "1.2.2")
class MySQLBackupPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        # ✅ 关键点：将传入的 config 绑定到 self.config
        self.config = config or {}
        
        # 临时存储路径
        self.tmp_dir = Path("./data/db_backups_tmp")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载 schema 默认值（备用方案）
        self.defaults = self._load_schema_defaults()

    def _load_schema_defaults(self) -> dict:
        """从 schema 文件读取默认配置喵"""
        schema_path = os.path.join(os.path.dirname(__file__), "_conf_schema.json")
        defaults = {}
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    for key, value in schema.items():
                        defaults[key] = value.get("default")
            except Exception as e:
                logger.warning(f"读取配置 schema 失败喵: {e}")
        return defaults

    def get_val(self, key: str):
        """快捷获取配置值，带兜底喵"""
        return self.config.get(key, self.defaults.get(key))

    @filter.command("db_backup")
    async def backup_database(self, event: AstrMessageEvent):
        """
        根据配置导出并发送数据库文件喵
        """
        try:
            # ✅ 直接从 self.config 或 defaults 中读取
            db_host = self.get_val("db_host") or "127.0.0.1"
            db_port = self.get_val("db_port") or 3306
            db_user = self.get_val("db_user") or "root"
            db_password = self.get_val("db_password") or ""
            backup_databases = self.get_val("backup_databases")

            if not backup_databases:
                yield event.plain_result("❌ 喵呜，配置里没找到要备份的库喵！请在管理面板确认。")
                return

            # 如果 backup_databases 是逗号分隔的字符串，处理成列表
            if isinstance(backup_databases, str):
                backup_databases = [d.strip() for d in backup_databases.split(",") if d.strip()]

            yield event.plain_result(f"🚀 任务开启！准备备份: {', '.join(backup_databases)} ...")

            for db_name in backup_databases:
                db_name = db_name.strip()
                if not db_name: continue
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = self.tmp_dir / f"{db_name}_{timestamp}.sql"
                
                try:
                    # 执行导出
                    await self.execute_mysqldump(db_host, db_port, db_user, db_password, db_name, file_path)
                    
                    if file_path.exists() and file_path.stat().st_size > 0:
                        file_size = os.path.getsize(file_path)
                        yield event.chain_result([
                            Plain(f"✅ 导出成功: {db_name} ({self.format_file_size_binary(file_size)})"),
                            File(str(file_path.absolute()))
                        ])
                        
                        # 给发送留出一点缓冲时间再删除喵
                        await asyncio.sleep(12) 
                        if file_path.exists():
                            os.remove(file_path)
                    else:
                        yield event.plain_result(f"⚠️ {db_name} 导出的文件好像是空的喵。")
                
                except Exception as e:
                    yield event.plain_result(f"⚠️ 导出 {db_name} 失败: {str(e)}")

        except Exception as e:
            logger.error(f"MySQL Backup Error: {e}", exc_info=True)
            yield event.plain_result(f"😿 喵呜，运行中发生故障: {str(e)}")

    async def execute_mysqldump(self, host, port, user, password, db, path):
        """执行 mysqldump 命令"""
        cmd = ["mysqldump", "-h", str(host), "-P", str(port), "-u", str(user)]
        if password: 
            cmd.append(f"-p{password}")
        cmd.extend(["--single-transaction", "--quick", str(db)])
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(stderr.decode('utf-8', errors='ignore'))
        
        with open(path, 'wb') as f:
            f.write(stdout)

    @staticmethod
    def format_file_size_binary(size_bytes: int) -> str:
        for unit in ['B', 'KiB', 'MiB', 'GiB']:
            if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TiB"