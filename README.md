# astrbot-mysql-backup

AstrBot 的 MySQL 数据库备份插件。

## 功能特性

- 📦 **自动备份** - 一键导出配置中的所有指定数据库
- 💾 **生成 SQL 文件** - 为每个数据库生成时间戳的 SQL 备份文件
- 📤 **即时反馈** - 将备份结果直接发送到聊天中
- ⚙️ **灵活配置** - 支持自定义数据库地址、端口、用户名和密码
- 🔒 **认证支持** - 完全支持数据库用户名和密码认证
- 📊 **文件管理** - 自动管理备份文件，支持显示文件大小和路径

## 安装依赖

### 1. 系统依赖

此插件需要系统上安装 MySQL 客户端工具（包含 `mysqldump`）：

```bash
# Ubuntu/Debian
sudo apt-get install mysql-client

# CentOS/RHEL
sudo yum install mysql

# macOS
brew install mysql-client
```

### 2. Python 依赖

插件会自动安装所需的 Python 依赖。

## 配置

编辑 `_conf_schema.json` 文件配置数据库连接信息：

```json
{
  "db_host": "127.0.0.1",
  "db_port": 3306,
  "db_user": "root",
  "db_password": "your_password",
  "backup_databases": ["neko_music", "other_db"]
}
```

### 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|------|------|
| `db_host` | string | 127.0.0.1 | MySQL 服务器地址 |
| `db_port` | int | 3306 | MySQL 服务器端口 |
| `db_user` | string | root | 数据库用户名 |
| `db_password` | string | 空 | 数据库密码（可选） |
| `backup_databases` | list | ["neko_music"] | 需要备份的数据库列表 |

## 使用方法

### 命令列表

在聊天中使用以下命令：

```
/db_backup   - 执行数据库备份
/db_help     - 显示帮助信息
```

### 工作流程

1. 输入 `/db_backup` 命令
2. 插件读取配置文件中的数据库信息
3. 使用 `mysqldump` 导出每个配置的数据库
4. 生成 `{数据库名}_{时间戳}.sql` 格式的备份文件
5. 将最新的备份文件信息发送到聊天中

### 备份文件位置

所有备份文件存储在：`./db_backups/` 目录

文件格式示例：`neko_music_20260503_211120.sql`

## 项目结构

```
astrbot_mysql_backup/
├── Main.py              # 插件主程序（使用大写 M）
├── metadata.yaml        # 插件元数据配置
├── _conf_schema.json    # 用户配置文件模板
├── README.md            # 项目文档
├── requirements.txt     # Python 依赖
└── LICENSE              # MIT 许可证
```

## 常见问题

### Q: 找不到 mysqldump 命令？
**A:** 请确保已安装 MySQL 客户端。使用上面提供的安装命令重新安装。

### Q: 连接被拒绝？
**A:** 检查以下事项：
- 数据库地址和端口是否正确
- 数据库是否在线
- 用户名和密码是否正确
- 网络连接是否正常

### Q: 权限不足？
**A:** 确保配置的数据库用户拥有以下权限：
- `SELECT`
- `LOCK TABLES`
- `SHOW VIEW`（可选）

### Q: 密码中包含特殊字符？
**A:** 使用强密码是安全的。插件会正确处理密码参数。

## 许可证

MIT

## 作者

Nyanyagulugulu (不穿胖次の小奶猫)

## 更新日志

### v1.0.0
- ✨ 初始版本
- 📦 支持单/多数据库备份
- 🔒 支持用户名和密码认证
- 📤 实时发送备份结果到聊天

