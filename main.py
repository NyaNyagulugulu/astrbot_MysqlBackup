import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import * 

@register("astrbot_plugin_mysql_backup", "数据库备份", "MySQL数据库直接发送备份插件", "1.2.3")
class MySQLBackupPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        # 绑定配置喵
        self.config = config or {}
        
        # 临时存储路径：./data/db_backups_tmp
        self.tmp_dir = Path("./data/db_backups_tmp")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载 schema 默认值作为兜底喵
        self.defaults = self._load_schema_defaults()

    def _load_schema_defaults(self) -> dict:
        """从同目录下的 _conf_schema.json 读取默认配置喵"""
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
        """优先从用户配置获取，没有则用默认值喵"""
        return self.config.get(key, self.defaults.get(key))

    @filter.command("db_backup")
    async def backup_database(self, event: AstrMessageEvent):
        """
        导出并发送数据库备份文件喵
        """
        try:
            # 读取配置信息喵
            db_host = self.get_val("db_host") or "127.0.0.1"
            db_port = self.get_val("db_port") or 3306
            db_user = self.get_val("db_user") or "root"
            db_password = self.get_val("db_password") or ""
            backup_databases = self.get_val("backup_databases")

            if not backup_databases:
                yield event.plain_result("❌ 喵呜，配置里没找到要备份的库喵！")
                return

            # 处理库名，支持列表或逗号分隔字符串喵
            if isinstance(backup_databases, str):
                db_list = [d.strip() for d in backup_databases.split(",") if d.strip()]
            else:
                db_list = backup_databases

            yield event.plain_result(f"🚀 任务开启！准备备份: {', '.join(db_list)} ...")

            for db_name in db_list:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = self.tmp_dir / f"{db_name}_{timestamp}.sql"
                
                try:
                    # 调用执行函数喵
                    await self.execute_mysqldump(db_host, db_port, db_user, db_password, db_name, file_path)
                    
                    if file_path.exists() and file_path.stat().st_size > 0:
                        file_size = os.path.getsize(file_path)
                        # 发送成功消息和文件喵
                        yield event.chain_result([
                            Plain(f"✅ 导出成功: {db_name}\n📊 大小: {self.format_file_size(file_size)}"),
                            File(str(file_path.absolute()))
                        ])
                        
                        # 异步等待一段时间后清理临时文件喵
                        asyncio.create_task(self.delayed_cleanup(file_path, 30))
                    else:
                        yield event.plain_result(f"⚠️ {db_name} 导出的文件为空，请检查权限喵。")
                
                except Exception as e:
                    yield event.plain_result(f"❌ 导出 {db_name} 失败: \n{str(e)}")

        except Exception as e:
            logger.error(f"MySQL Backup Error: {e}", exc_info=True)
            yield event.plain_result(f"😿 喵呜，运行中发生故障: {str(e)}")

    async def execute_mysqldump(self, host, port, user, password, db, path):
        """执行 mysqldump 核心逻辑喵"""
        # --column-statistics=0 是解决主人刚才那个报错的关键喵！
        cmd = [
            "mysqldump", 
            "-h", str(host), 
            "-P", str(port), 
            "-u", str(user),
            "--single-transaction", 
            "--quick",
            "--column-statistics=0" 
        ]
        
        if password: 
            cmd.append(f"-p{password}")
        
        cmd.append(str(db))
        
        # 使用异步子进程执行喵
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            # 排除掉密码警告信息，如果还有其他内容才是真的报错喵
            if "error" in error_msg.lower() or "can't" in error_msg.lower() or "unknown" in error_msg.lower():
                raise RuntimeError(error_msg)
        
        # 将 stdout 写入文件喵
        with open(path, 'wb') as f:
            f.write(stdout)

    async def delayed_cleanup(self, path: Path, delay: int):
        """延迟删除文件，确保文件已经发送出去喵"""
        await asyncio.sleep(delay)
        if path.exists():
            try:
                os.remove(path)
            except:
                pass

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小喵"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"