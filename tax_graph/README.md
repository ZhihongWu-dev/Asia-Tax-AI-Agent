# tax_graph：运行与交接

配套目录为同级的 `official/`。所有命令在同时包含这两个目录的项目根目录执行，路径均为相对路径。源资料目录未修改；这里的修改用于让这两个目录可以独立交接。

## 环境与依赖

税务引擎、规则编译、规划器及下面的案例命令在 Python 3.12.7 下验证，仅使用 Python 标准库，不需要指定 conda 环境，也不需要调用大模型。包含向量表的完整资料库在 Python 3.9.23 下重建，所用依赖版本列在 `official/requirements.txt` 和 `official/requirements-dense.txt`。

```bash
python --version
python -m pip install -r official/requirements.txt
```

上述依赖用于重建官方资料库。首次转换旧版 Office 文档还需 LibreOffice；放在 `PATH` 中或通过 `SOFFICE` 环境变量指定其可执行文件即可。已有转换缓存可复用。重建知识层会沿用 `official/_index/dense_model.txt` 指定的向量模型；全部缓存命中时只需要 NumPy，有未缓存的文本时需安装 `official/requirements-dense.txt` 并下载该模型。稠密查询也需要这些可选依赖。若只需要基础资料、词面检索与关系图，可使用 `python official/tools/build.py --no-dense`；它不生成向量表，发布的数据库则保留完整向量表。

数据库通过 Git LFS 保存；克隆时需安装 Git LFS，并在仓库根目录执行：

```bash
git lfs pull
```

## 构建与检查

```bash
python official/tools/build.py
python -m tax_graph.rules
python -m tax_graph.check_engine
python -m tax_graph.check_fields
python -m tax_graph.check_extract
python -m tax_graph.check_scope
python tax_graph/validation/run_checks.py
```

`build.py` 重建 `official.sqlite`、条款 CSV 和构建报告；发生构建或知识层检查错误时返回非零退出码。规则编译核对参数、数值引语和法条引用。实际验证结果见 [validation/README.md](validation/README.md)，配套资料核对见 [official/HANDOFF.md](../official/HANDOFF.md)。

## 已运行的案例

```bash
python -m tax_graph.run tax_graph/examples/meridian.json --out-dir tax_graph/examples/results
python -m tax_graph.run tax_graph/examples/meridian.json --table --out-dir tax_graph/examples/results
python -m tax_graph.run tax_graph/examples/hk_holding_services.synthetic.json --table --out-dir tax_graph/examples/results
```

- [meridian.json](examples/meridian.json)：源项目标记为真实案例的新加坡公司向上海客户提供服务的场景。真实性依据项目说明，未核验外部凭证；文件中的日期等假设保留在 `notes`。配套答复是 [meridian.answers.json](examples/meridian.answers.json)。输出是运行结果，不是税务专家确认的标准答案。
- [hk_holding_services.synthetic.json](examples/hk_holding_services.synthetic.json)：从源测试电池复制的香港相关模拟案例，用于验证香港场景可以执行，不代表真实业务。

运行结果保存在 [examples/results/](examples/results/)。`--out-dir` 指定输出位置；不指定时保留原有 `out/` 默认行为。待补事实仍显示为待补，不会填造答案。

## 文档提取器

[信息收集.md](信息收集.md) 是从源项目逐字复制的字段与证据规范。`llm/extract.py` 和 `check_fields.py` 均读取包内这份文件，不依赖仓库外的同名文件。

提取器接受调用方提供的模型函数，模型须返回规定的 JSON。`check_extract` 使用确定性的测试函数，不访问在线模型；生产使用的模型、鉴权和文档解析方式由接入方配置。

接口、页面、两套系统的数据转换和数据库连接属于集成侧工作，本次交接提供可运行引擎、配套资料和验证结果。
