# 🐾 AstrBot MySQL Backup Plugin (Docker 适配版)

[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-orange?style=flat-square)](https://github.com/Soulter/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.14-blue?style=flat-square)](https://www.python.org/)

本插件专为运行在 Docker 环境下的 **AstrBot/NapCat** 架构设计，深度优化了宿主机与容器间的大文件传输逻辑[cite: 1]。针对 **Neko Music (Neko云音乐)** 等拥有大量无损音乐元数据的数据库进行了高性能适配，解决了传统传输方式在处理大体积 SQL 时可能出现的 `retcode=1200` 报错问题喵！(˵^◡^˵)

## ✨ 核心特性

*   **物理挂载共享**：利用宿主机与容器的 `/tmp` 目录挂载关联，避开 Base64 编码带来的内存开销与传输校验错误[cite: 1]。
*   **零内存积压**：通过 `mysqldump` 的 `--result-file` 参数直接写入磁盘，确保在 **Xeon E5** 等多核服务器上依然保持极低的 CPU 和内存占用。
*   **智能自动清理**：备份成功后自动执行异步清理任务，防止 `/tmp` 分区因多次备份而爆满喵。
*   **精准度量显示**：输出信息遵循 IEC 标准（KiB/MiB/GiB），适配全栈开发者的阅读习惯。

## 🛠️ 环境准备

### 1. 目录挂载 (关键步骤 喵！)
由于插件运行在宿主机环境或特定容器，而 NapCat 运行在另一个容器中，必须通过物理挂载让它们“共享”同一个临时空间。

在你的 `docker-compose.yaml` 中，请确保 NapCat 容器有如下配置：
```yaml
services:
  napcat:
    volumes:
      - /tmp:/tmp  # 将宿主机的 /tmp 挂载到容器内 喵！