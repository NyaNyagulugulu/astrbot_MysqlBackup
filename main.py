import os
import asyncio
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import * 

@register("astrbot_plugin_mysql_backup", "数据库备份", "MySQL数据库直接发送备份插件", "1.1.8")
class MySQLBackupPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 临时目录：建议放在 data 目录下
        self.tmp_dir = Path("./data/db_backups_tmp")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    @filter.command("db_backup")
    async def backup_database(self, event: AstrMessageEvent):
        """
        备份数据库并发送文件喵！
        """
        try:
            # 尝试获取插件配置
            # 注意：请确保在插件管理界面已经正确填写了这些字段
            plugin_config = self.context.get_config("astrbot_plugin_mysql_backup")
            if not plugin_config:
                # 兼容性处理：如果上面的拿不到，尝试拿自身的 config
                plugin_config = self.config if hasattr(self, "config") else {}

            db_host = plugin_config.get("db_host", "127.0.0.1")
            db_port = plugin_config.get("db_port", 3306)
            db_user = plugin_config.get("db_user", "root")
            db_password = plugin_config.get("db_password", "")
            backup_databases = plugin_config.get("backup_databases", [])

            if not backup_databases:
                yield event.plain_result("❌ 配置文件里没写要备份哪个库喵！请先在配置界面添加数据库列表。")
                return

            yield event.plain_result(f"🚀 任务开启！准备备份 {len(backup_databases)} 个数据库喵...")

            for db_name in backup_databases:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = self.tmp_dir / f"{db_name}_{timestamp}.sql"
                
                try:
                    # 执行导出
                    await self.execute_mysqldump(db_host, db_port, db_user, db_password, db_name, file_path)
                    
                    if file_path.exists() and file_path.stat().st_size > 0:
                        file_size = os.path.getsize(file_path)
                        size_str = self.format_file_size_binary(file_size)
                        
                        # 构建消息链
                        chain = [
                            Plain(f"✅ [{db_name}] 导出成功！\n文件大小：{size_str}\n正在即时上传，请稍候喵..."),
                            File(str(file_path.absolute()))
                        ]
                        yield event.chain_result(chain)
                        
                        # 稍微等一下让框架把文件读取并发送出去
                        await asyncio.sleep(8) 
                        if file_path.exists():
                            os.remove(file_path)
                    else:
                        yield event.plain_result(f"⚠️ 备份 {db_name} 失败：导出的文件为空喵，请检查数据库权限。")
                
                except Exception as e:
                    yield event.plain_result(f"⚠️ 备份 {db_name} 时出错了：{str(e)}")

        except Exception as e:
            logger.error(f"MySQL备份插件运行异常: {e}", exc_info=True)
            yield event.plain_result(f"😿 糟糕，发生系统级错误：{str(e)}")

    @filter.command("db_help")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "🔧 数据库备份插件指南：\n"
            "1. 使用 /db_backup 触发备份。\n"
            "2. 插件会自动从配置中读取库名并导出。\n"
            "3. 单位采用二进制 GiB/MiB 换算，安全起见，本地不留存备份文件喵！"
        )
        yield event.plain_result(help_text)

    async def execute_mysqldump(self, host, port, user, password, db, path):
        """执行 mysqldump 逻辑"""
        # 使用列表形式避免 Shell 注入风险
        cmd = ["mysqldump", "-h", host, "-P", str(port), "-u", user, "--single-transaction", "--quick"]
        if password: 
            cmd.append(f"-p{password}")
        cmd.append(db)
        
        # 异步执行
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            raise RuntimeError(f"mysqldump 返回非零状态码: {error_msg}")
        
        # 将结果写入文件
        with open(path, 'wb') as f:
            f.write(stdout)

    @staticmethod
    def format_file_size_binary(size_bytes: int) -> str:
        """KiB, MiB, GiB 换算 (1024 进制)"""
        if size_bytes == 0: return "0 B"
        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
        i = 0
        while size_bytes >= 1024 and i < len(units)-1:
            size_bytes /= 1024
            i += 1
        return f"{size_bytes:.2f} {units[i]}"