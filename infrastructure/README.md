# Infrastructure

本目录保存基础设施与本地环境配置。

`postgres/docker-compose.yml` 提供 L0 本地研究使用的 PostgreSQL / pgvector 服务，可通过仓库根目录的 `make db-up` 启动。数据库迁移位于 `alembic/`。

此配置用于本地开发；正式部署仍需确定部署地区、租户隔离、身份认证、数据保留和恢复要求。
