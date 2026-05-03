import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import * 

@register("astrbot_plugin_mysql_backup", "数据库备份", "MySQL备份(挂载共享版)", "1.5.0")
class MySQLBackupPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        # 核心：使用挂载共享的 tmp 目录 喵！
        self.share_tmp_dir = Path("/tmp/astrbot_db_backups")
        self.share_tmp_dir.mkdir(parents=True, exist_ok=True)
        self.defaults = self._load_schema_defaults()

    def _load_schema_defaults(self) -> dict:
        schema_path = os.path.join(os.path.dirname(__file__), "_conf_schema.json")
        defaults = {}
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    for key, value in schema.items():
                        defaults[key] = value.get("default")
            except Exception as e:
                logger.warning(f"读取配置失败喵: {e}")
        return defaults

    def get_val(self, key: str):
        return self.config.get(key, self.defaults.get(key))

    @filter.command("db_backup")
    async def backup_database(self, event: AstrMessageEvent):
        """利用挂载共享目录进行超快速备份 喵！"""
        try:
            db_host = self.get_val("db_host") or "127.0.0.1"
            db_port = self.get_val("db_port") or 3306
            db_user = self.get_val("db_user") or "root"
            db_password = self.get_val("db_password") or ""
            backup_databases = self.get_val("backup_databases")

            if not backup_databases:
                yield event.plain_result("❌ 喵！主人还没告诉我要备份哪个库喵！")
                return

            db_list = [d.strip() for d in backup_databases.split(",")] if isinstance(backup_databases, str) else backup_databases
            yield event.plain_result(f"📂 检测到挂载共享目录，启动高效物理传输模式...")

            for db_name in db_list:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"{db_name}_{timestamp}.sql"
                # 文件直接写在共享目录下 喵
                file_path = self.share_tmp_dir / file_name
                
                try:
                    # 导出数据库 喵
                    await asyncio.wait_for(
                        self.execute_mysqldump(db_host, db_port, db_user, db_password, db_name, file_path),
                        timeout=300.0
                    )
                    
                    if file_path.exists() and file_path.stat().st_size > 0:
                        file_size = os.path.getsize(file_path)
                        size_str = self.format_file_size_iec(file_size)
                        
                        # 因为是挂载共享，Docker 里的 NapCat 也能直接通过绝对路径看到这个文件 喵！
                        # 这种方式最稳定，不会再报 1200 参数缺失了
                        yield event.chain_result([
                            Plain(f"✅ {db_name} 备份成功！\n📊 大小: {size_str}\n📍 路径: {file_path}"),
                            File(file=str(file_path), name=file_name) 
                        ])
                        
                        # 稍微留一点时间让文件发送，然后清理 喵
                        asyncio.create_task(self.delayed_cleanup(file_path, 120))
                    else:
                        yield event.plain_result(f"⚠️ {db_name} 备份失败，文件为空喵。")
                
                except Exception as e:
                    yield event.plain_result(f"❌ {db_name} 备份失败喵: {str(e)}")

        except Exception as e:
            logger.error(f"Global Error: {e}", exc_info=True)
            yield event.plain_result(f"😿 引擎故障喵: {str(e)}")

    async def execute_mysqldump(self, host, port, user, password, db, path):
        """直接写到共享磁盘路径，速度起飞 喵！"""
        cmd = [
            "mysqldump", "-h", str(host), "-P", str(port), "-u", str(user),
            "--single-transaction", "--quick", "--column-statistics=0", "--hex-blob",
            f"--result-file={path}", str(db)
        ]
        if password: 
            cmd.insert(9, f"-p{password}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode('utf-8', errors='ignore'))

    async def delayed_cleanup(self, path: Path, delay: int):
        await asyncio.sleep(delay)
        if path.exists():
            try:
                os.remove(path)
            except: pass

    @staticmethod
    def format_file_size_iec(size_bytes: int) -> str:
        if size_bytes == 0: return "0 B"
        units = ("B", "KiB", "MiB", "GiB")
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        if i >= len(units): i = len(units) - 1
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {units[i]}"