# 🔍 SSD性能测试工具

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.5.0-orange.svg)](CHANGELOG.md)
[![FIO Version](https://img.shields.io/badge/FIO-3.4%2B-red.svg)](https://fio.readthedocs.io)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.linux.org)

一个专业级的SSD性能测试工具，基于FIO（Flexible I/O Tester）提供全面、准确的存储设备性能评估。

## 📋 目录

- [✨ 功能特性](#-功能特性)
  - [🔄 数据提取与单位转换](#-数据提取与单位转换-v250重要更新)
- [🚀 快速开始](#-快速开始)
  - [系统要求](#系统要求)
  - [安装指南](#安装指南)
  - [基础使用](#基础使用)
- [⚙️ 详细使用](#️-详细使用)
  - [命令行参数](#命令行参数)
  - [使用示例](#使用示例)
  - [测试流程](#测试流程)
- [📊 结果解读](#-结果解读)
- [🤝 贡献指南](#-贡献指南)
- [📄 许可证](#-许可证)
- [📞 支持与反馈](#-支持与反馈)

## 🌟 项目概述

这是一个基于Python的SSD性能测试工具，专为专业存储性能评估而设计。通过标准化的测试流程和科学的统计分析，为SSD提供准确的性能基准测试。工具采用六阶段测试流程，支持多种设备类型，并提供了详细的性能分析和报告生成功能。

## ✨ 功能特性

### 🎯 核心测试功能
- **🔄 四种标准测试模式**
  - 128K顺序读/写测试（大文件传输性能）
  - 4K随机读/写测试（小文件操作性能）
- **📊 专业数据分析**
  - 多次采样确保数据可靠性
  - 变异系数（CV）评估数据稳定性
  - 详细的性能统计和可视化报告
- **⚙️ 灵活配置选项**
  - 可自定义测试时间、队列深度、并发线程数
  - 支持多种设备类型（NVMe、SATA SSD、HDD）
  - 智能参数适配和预热策略
- **📈 全面报告输出**
  - CSV格式便于Excel分析
  - JSON格式支持程序化处理
  - 彩色终端输出提升可读性

### 🛠️ 技术特性
- **FIO集成**: 基于3.4+版本FIO，确保测试准确性
- **防作弊机制**: 使用`--refill_buffers`参数避免SSD压缩/去重优化干扰
- **设备适配**: 自动识别设备类型并优化参数配置
- **稳定性分析**: 基于变异系数(CV)评估数据质量
- **多格式报告**: 支持CSV、JSON、TXT多种输出格式

### 🔄 数据提取与单位转换 (v2.5.0重要更新)

**技术升级说明**:
- **数据源优化**: 从FIO JSON输出中直接提取`bw_bytes`替代`bw`字段，确保数据精度
- **单位标准化**: 所有顺序读写性能输出统一使用**MB/s**单位（替代之前的MiB/s）
- **转换公式**: `1 MiB/s = 1.048576 MB/s`，确保与其他存储工具的单位一致

**单位转换详情**:
```bash
# 数据提取流程
FIO输出: bw_bytes (bytes/sec)
↓
转换为MiB/s: bw_bytes ÷ 1,048,576 
↓  
转换为MB/s: MiB/s × 1.048576
```

**影响范围**:
- ✅ 顺序读写测试结果显示
- ✅ CSV和JSON报告导出
- ✅ 性能评估标准
- ✅ 终端输出格式
- ❌ 随机读写IOPS测试（不受影响，仍使用IOPS单位）

## 🚀 快速开始

### 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **操作系统** | Linux (Ubuntu 18.04+) | Ubuntu 20.04+ / CentOS 8+ |
| **Python** | 3.6+ | 3.8+ |
| **FIO** | 3.4+ | 3.41+ |
| **权限** | root/sudo | root/sudo |
| **内存** | 2GB | 4GB+ |
| **存储空间** | 100MB | 1GB+ |

> ⚠️ **重要提醒**: FIO版本对性能测试结果有显著影响，强烈建议使用3.4+版本

### FIO版本要求说明

⚠️ **重要提醒**: FIO版本对性能测试结果有显著影响，强烈建议使用3.4+版本

#### 历史性能问题概述

**2.x版本存在的问题**:
- 在2.1.7和2.8版本中，`refill_buffers`参数存在严重的性能问题
- 每次IO操作都会调用随机数生成器和`memcpy`操作
- GitHub Issue #40 (2014年) 和 #157 (2016年) 详细记录了这些问题
- 在某些场景下可导致测试带宽骤降50%以上

#### 3.x版本的演进优化

**3.0-3.3版本**:
- 引入批量预生成随机页(`rand_page`)机制
- 实现SIMD加速的打乱操作
- 开始将refill操作从submit路径移除

**3.4+版本 (推荐)**:
- ✅ 所有性能优化默认启用
- ✅ `scramble_buffers=1`成为轻量级替代方案
- ✅ 彻底解决了refill_buffers的性能开销问题

#### 版本选择建议

| FIO版本 | 状态 | 推荐度 | 说明 |
|---------|------|-------|------|
| < 2.8 | ❌ 不推荐 | 🚫 | 存在严重的refill_buffers性能问题 |
| 2.8-3.3 | ⚠️ 可用 | ⚠️ | 部分优化，但仍可能有性能影响 |
| 3.4+ | ✅ 推荐 | ✅ | 所有优化默认启用，性能最佳 |
| 3.41+ | 🔥 最新 | 🔥 | 完全解决历史问题，测试结果最准确 |

#### 技术原理详解

**官方文档(3.41版本)说明**:
> `refill_buffers`会在每次submit时重填缓冲区，若仅为绕过主机去重/压缩且担心CPU消耗，建议使用轻量级的`scramble_buffers=1`。

**性能优化的技术实现**:
1. **批量预生成**: 一次性生成大量随机数据页，避免频繁调用随机数生成器
2. **SIMD加速**: 利用CPU向量指令加速数据打乱操作  
3. **异步处理**: 将refill操作移至worker线程的空闲时间批处理
4. **内存优化**: 减少不必要的内存拷贝操作

#### --refill_buffers参数详解

##### 🎯 参数作用机制

`--refill_buffers`是FIO中一个关键的性能测试参数，它的主要作用是**关闭SSD测试中的"作弊通道"**，确保测试结果反映真实的应用场景性能。

##### 🔍 技术原理分析

**1. SSD作弊机制的工作原理**

现代SSD普遍采用两种主要的性能优化策略，这些策略在正常使用中是有益的，但在性能测试中会成为"作弊通道":

```bash
# 数据压缩机制
# SSD控制器检测到可压缩数据时，实际写入的数据量会显著减少
原始数据: "AAAAAAAAAAAA..." (高度可压缩)
压缩后:  "A×12" (压缩比可能达到10:1)
结果:   1GB数据 → 实际只写入100MB，测得的带宽"虚高"

# 数据去重机制  
# SSD检测到重复数据块时，通过元数据引用避免重复写入
原始数据: [Block_A, Block_A, Block_A, Block_A]
去重后:  [Block_A] + 4个引用指针
结果:   4GB数据 → 实际只写入一个Block，测得的带宽"虚高"
```

**2. --refill_buffers的对抗策略**

```bash
# 未使用refill_buffers时的测试流程
+-------------------+     +-----------------+     +------------------+
| 生成测试数据缓冲区 | →   | 多次使用相同数据 | →   | SSD识别并压缩/去重 | 
| (一次性生成随机数据)|   | (每轮IO复用)     |   | (带宽测试结果虚高) |
+-------------------+     +-----------------+     +------------------+

# 使用refill_buffers时的测试流程  
+-------------------+     +-------------------+     +-------------------+
| 生成测试数据缓冲区 | →   | 每次submit重填缓冲区 | →   | SSD接收完全不同的数据|
| (每次重新随机生成)  |   | (破除数据模式识别)   |   | (真实带宽性能)      |
+-------------------+     +-------------------+     +-------------------+
```

##### 📊 性能影响量化分析

**理论带宽差异计算**:

```bash
# 场景1: 压缩型SSD测试高可压缩数据
无refill_buffers: 
- 输入数据: 1GB高度可压缩数据 (如全零数据)
- SSD实际处理: 100MB (压缩比10:1)  
- 测试带宽: 5000 MB/s (虚高10倍)
真实带宽: 500 MB/s

有refill_buffers:
- 输入数据: 1GB完全随机数据 (不可压缩)
- SSD实际处理: 1GB (无压缩效果)
- 测试带宽: 500 MB/s (真实性能)

# 场景2: 去重型SSD测试重复数据  
无refill_buffers:
- 输入数据: 1GB重复数据块
- SSD实际处理: 1个数据块 + 元数据
- 测试带宽: 8000 MB/s (虚高数十倍)
真实带宽: 400 MB/s

有refill_buffers:
- 输入数据: 1GB完全不重复数据
- SSD实际处理: 1GB (无去重效果)  
- 测试带宽: 400 MB/s (真实性能)
```

##### 🎯 对顺序写带宽的特定影响

**顺序写性能的真实性验证**:

```bash
# SSD顺序写的两种工作模式

# 模式A: 压缩/去重优化模式 (无refill_buffers)
FIO写入: [AAAA][AAAA][AAAA][AAAA] → SSD识别为重复模式
SSD处理: 记录"A模式"+计数器 → 实际物理写入极小
测试结果: 带宽数值虚高，不能反映真实顺序写性能

# 模式B: 真实顺序写模式 (有refill_buffers)  
FIO写入: [random1][random2][random3][random4] → SSD无法识别模式
SSD处理: 每个块都要实际写入闪存颗粒 → 反映真实物理性能
测试结果: 带宽数值真实，反映盘面实际顺序写能力
```

##### 🔧 参数配置的技术细节

**FIO命令行配置**:

```bash
# 基础配置 (关闭作弊通道 + 预热机制)
fio --name=test \
    --filename=/dev/nvme0n1 \
    --rw=write \
    --bs=128k \
    --runtime=600 \
    --ramp_time=300 \       # 前300秒预热，后300秒正式测试
    --refill_buffers \      # 每次submit重新填充缓冲区
    --randrepeat=0 \        # 随机模式不重复
    --norandommap=1 \       # 不使用随机映射缓存
    --end_fsync=1           # 确保数据完全写入
```

**参数协同机制**:

```bash
# 参数间的协同工作原理
refill_buffers + randrepeat=0 + norandommap=1
├── refill_buffers:     每次IO提交时重新生成数据
├── randrepeat=0:        确保随机模式每次都不同  
└── norandommap=1:       禁用随机映射，强制实际IO
```

##### ⚡ CPU开销与性能权衡

**3.41版本的优化方案**:

```bash
# 传统refill_buffers (2.x版本)
CPU开销: 高 (每次IO调用随机数生成器 + memcpy)
影响:   测试带宽可能下降15-30%

# 优化后refill_buffers (3.4+版本)  
CPU开销: 低 (批量预生成 + SIMD加速 + 异步处理)
影响:   测试带宽下降<5%，但结果更准确

# 轻量级替代方案 (3.41版本可用)
scramble_buffers=1:
- 仅对现有数据进行轻度打乱
- CPU开销极低 (<1%)
- 能有效绕过大部分压缩/去重优化
- 适用于对CPU消耗敏感的测试场景
- 注意：这是3.41版本的默认设置(default: 1)
```

##### 🎯 实际测试建议

**测试配置最佳实践**:

```bash
# 1. 标准性能测试 (推荐)
--refill_buffers --randrepeat=0 --norandommap=1
# 目标: 获取最真实的SSD物理性能数据

# 2. CPU敏感测试场景  
--scramble_buffers=1 --randrepeat=0
# 目标: 平衡测试准确性和CPU消耗

# 3. 对比测试建议
# 分别运行有无refill_buffers的测试
# 差异>20%说明SSD有较强的压缩/去重优化
```

**结果解读指南**:

```bash
# 当refill_buffers导致性能显著下降时:
下降比例 < 15%:  SSD压缩/去重能力有限，性能相对真实
下降比例 15-50%: SSD有明显优化，需关注真实性能需求  
下降比例 > 50%: SSD heavily optimized，refill_buffers测试结果更具参考价值
```

通过`--refill_buffers`参数，我们能够**穿透SSD的软件优化层，直接测量其硬件物理性能**，这对于评估SSD在真实不可压缩数据负载下的表现至关重要。

#### 版本验证方法

```bash
# 检查FIO版本
fio --version

# 验证是否支持scramble_buffers参数
fio --cmdhelp=scramble_buffers

# 验证refill_buffers参数详情
fio --cmdhelp=refill_buffers
```

**📚 官方文档参考**:
- FIO官方文档: https://fio.readthedocs.io/en/latest/fio_doc.html
- 版本更新日志: https://fio.readthedocs.io/en/latest/fio_doc.html#change-log

### 依赖项安装

```bash
# Ubuntu/Debian系统 (推荐安装最新版本)
sudo apt-get update
# 方法1: 从官方源安装
sudo apt-get install fio python3 python3-pip

# 方法2: 如需3.4+版本，可从官方PPA安装
sudo add-apt-repository ppa:flexiondotorg/fio
sudo apt-get update
sudo apt-get install fio

# CentOS/RHEL系统
sudo yum install fio python3 python3-pip

# 或从EPEL源安装更新版本
sudo yum install epel-release
sudo yum install fio python3 python3-pip

# 源码编译安装 (确保获取最新版本)
# 访问 https://fio.readthedocs.io/en/latest/fio_doc.html 获取最新版本
wget http://brick.kernel.dk/snaps/fio-3.41.tar.gz
tar xzf fio-3.41.tar.gz
cd fio-3.41
./configure
make && sudo make install

# 安装Python依赖（如果有requirements.txt）
pip3 install -r requirements.txt
```

### 基础使用

```bash
# 基础测试（使用默认配置）
sudo python3 ssd_perf_test.py nvme0n1

# 启用调试模式
sudo python3 ssd_perf_test.py /dev/sda -d

# 自定义测试时间（60秒）
sudo python3 ssd_perf_test.py nvme0n1 -t 60

# 高性能配置测试
sudo python3 ssd_perf_test.py nvme0n1 -q 128 -j 8 -t 120
```

### 🎯 一键安装脚本

```bash
# 下载并运行安装脚本
curl -fsSL https://raw.githubusercontent.com/your-username/ssd-perf-test/main/install.sh | bash

# 手动克隆安装
git clone https://github.com/your-username/ssd-perf-test.git
cd ssd-perf-test
chmod +x install.sh && sudo ./install.sh
```

## ⚙️ 详细使用

### 命令行参数

```bash
python3 ssd_perf_test.py [选项] <设备名>

必需参数:
    <设备名>         要测试的SSD设备名 (如: sda, nvme0n1)

可选参数:
    -t, --time      预热和测试持续时间 (默认: 600秒)
    -q, --queue     队列深度 (默认: 32)
    -j, --jobs      并发线程数 (默认: 4)
    -d, --debug     启用调试模式
    --size          自定义测试大小 (默认: 100%,例如: 10G, 500M, 20%, 100%)
    --ramp_time     预热时间 (默认: 自动设置为-t参数值的一半)
    -h, --help      显示帮助信息
```

### 📋 参数对照表

| 参数 | 默认值 | 适用场景 | 建议值 |
|------|--------|----------|--------|
| `-t` | 600秒 | 标准测试 | 600秒 |
| `-q` | 32 | SATA SSD | 32-64 |
| `-q` | 32 | NVMe SSD | 64-128 |
| `-j` | 4 | SATA SSD | 2-4 |
| `-j` | 4 | NVMe SSD | 4-8 |

### 使用示例

#### 1. 标准性能测试

```bash
# 测试NVMe SSD
sudo python3 ssd_perf_test.py nvme0n1

# 测试SATA SSD
sudo python3 ssd_perf_test.py sda

# 启用详细调试信息
sudo python3 ssd_perf_test.py nvme0n1 -d
```

#### 2. 自定义配置测试

```bash
# 短时间测试（适用于快速验证）
sudo python3 ssd_perf_test.py nvme0n1 -t 60

# 高性能测试配置
sudo python3 ssd_perf_test.py nvme0n1 -q 128 -j 8

# 限制测试范围
sudo python3 ssd_perf_test.py sda --size 50G
```

#### 3. 自定义预热时间

```bash
# 手动指定预热时间为30秒
sudo python3 ssd_perf_test.py nvme0n1 --ramp_time 30 -t 120
```

## ⚙️ 配置选项详解

### 测试流程说明

工具采用六阶段测试流程：

1. **第一阶段**: 顺序写预热（独立预热，使用--ramp_time参数作为完整运行时间）
2. **第二阶段**: 128K顺序写入测试（使用--ramp_time内置预热 + 正式测试）
3. **第三阶段**: 128K顺序读取测试（使用--ramp_time内置预热 + 正式测试）
4. **第四阶段**: 随机写预热（独立预热，使用--ramp_time参数作为完整运行时间）
5. **第五阶段**: 4K随机写入测试（使用--ramp_time内置预热 + 正式测试）
6. **第六阶段**: 4K随机读取测试（使用--ramp_time内置预热 + 正式测试）

### 参数配置方案

#### 主测试阶段参数
```
--runtime:     使用-t参数指定的总测试时间 (默认: 600秒)
--ramp_time:   内置预热时间，自动设置为runtime值的1/2 (默认: 300秒)
有效测量时间:   runtime - ramp_time (默认: 300秒)
预热机制:       前ramp_time秒为预热期，后续时间为正式测试期
```

#### 独立预热阶段参数
```
--runtime:     使用ramp_time值作为完整预热时间 (默认: 300秒)
预热方式:     独立预热阶段，专门用于设备状态预热
预热目标:     确保SSD达到稳定工作状态，提高后续测试准确性
```

### 设备类型适配

| 设备类型 | 默认队列深度 | 默认线程数 | 适用场景 |
|---------|-------------|-----------|---------|
| NVMe SSD | 64+ | 4+ | 高性能企业级SSD |
| SATA SSD | 32+ | 2+ | 消费级SSD |
| HDD | ≤16 | ≤2 | 机械硬盘 |

## 📊 结果解读

### 📁 输出文件结构

测试完成后会在当前目录生成结果文件夹（格式：`results_{设备名}_{时间戳}`），包含以下文件：

```
results_nvme0n1_20231216_1530/
├── 📈 performance_report.csv    # CSV格式性能数据
├── 📄 performance_report.json   # JSON详细报告
└── 📋 system_info.txt           # 系统信息摘要
```

### 📈 性能指标说明

| 指标类型 | 单位 | 优秀标准 | 良好标准 |
|----------|------|----------|----------|
| **顺序读取** | MB/s | >5000 | >3000 |
| **顺序写入** | MB/s | >2000 | >1000 |
| **随机读取** | IOPS | >500K | >300K |
| **随机写入** | IOPS | >400K | >200K |

### 🎯 CV稳定性评估

#### 📊 数据可靠性分级

| 平均CV值 | 稳定性描述 | 可靠性等级 | 建议 |
|----------|------------|------------|------|
| **CV < 0.01** | 数据极其稳定 | 极高 | 测试结果高度可靠，可用于重要性能评估 |
| **0.01 ≤ CV < 0.05** | 数据高度稳定 | 很高 | 测试结果可靠，建议作为基准性能参考 |
| **0.05 ≤ CV < 0.1** | 数据稳定性优秀 | 高 | 测试结果较为可靠，适合一般性能评估 |
| **CV ≥ 0.1** | 数据存在波动 | 中等 | 建议增加测试次数以获得更稳定的结果 |

#### 🔍 CV质量分布分析

工具会统计所有测试项目的CV质量分布：
- **优秀 (CV < 0.05)**：数据质量极高的测试项目数量
- **良好 (0.05 ≤ CV < 0.1)**：数据质量良好的测试项目数量  
- **波动较大 (CV ≥ 0.1)**：需要改进稳定性的测试项目数量

#### 💡 评估结果解读

**输出示例**：
```
🎯 数据稳定性评估结论
  🔍 稳定性: 数据稳定性优秀 (平均CV: 0.085)
  🎯 可靠性: 高
  💡 建议: 测试结果较为可靠，适合一般性能评估

📊 CV质量分布
  优秀(CV<0.05): 1/4 项测试
  良好(0.05≤CV<0.1): 2/4 项测试
  波动较大(CV≥0.1): 1/4 项测试
```

**稳定性判定标准**：
- **CV值**：标准差与均值的比值，衡量数据的相对波动程度
- **平均CV**：所有测试项目CV值的算术平均，反映整体稳定性
- **质量分布**：展示不同稳定性级别的测试项目占比情况

### 🖼️ 截图示例

> 💡 **提示**: 在实际使用中，您可以添加以下截图来展示工具效果：
> ```
> /screenshots/
> ├── terminal_output.png      # 终端输出截图
> ├── performance_graph.png    # 性能对比图表
> └── test_results.png         # 测试结果界面
> ```

## ❓ 常见问题解答

### Q1: 提示"设备不存在"或"权限不足"
```bash
# 确认设备存在
ls -la /dev/nvme*
ls -la /dev/sd*

# 使用sudo权限运行
sudo python3 ssd_perf_test.py nvme0n1
```

### Q2: FIO命令未找到或版本过低
```bash
# 检查FIO版本
fio --version

# 如果版本<3.4，建议升级
# 参考: https://fio.readthedocs.io/en/latest/fio_doc.html

# Ubuntu/Debian - 安装最新版本
sudo add-apt-repository ppa:flexiondotorg/fio
sudo apt-get update
sudo apt-get install fio

# CentOS/RHEL - 从EPEL安装
sudo yum install epel-release
sudo yum install fio

# 源码编译安装最新版本
wget http://brick.kernel.dk/snaps/fio-3.41.tar.gz
tar xzf fio-3.41.tar.gz
cd fio-3.41
./configure
make && sudo make install
```

### Q3: 测试结果不稳定（CV值过高）
```bash
# 延长测试时间
sudo python3 ssd_perf_test.py nvme0n1 -t 300

# 检查系统负载，确保测试期间无其他IO密集型任务
```

### Q4: 设备类型识别错误
```bash
# 手动查看设备类型
cat /sys/block/nvme0n1/queue/rotational  # 0=SSD, 1=HDD
```

### Q5: 测试时间过长如何优化？
```bash
# 快速验证模式（30秒测试）
sudo python3 ssd_perf_test.py nvme0n1 -t 30

# 减少测试数据量
sudo python3 ssd_perf_test.py nvme0n1 --size 10G
```

### Q6: 为什么需要使用3.4+版本的FIO？
```bash
# 版本差异对比测试
# 使用旧版本可能有refill_buffers性能开销
# 3.4+版本通过以下优化解决该问题：

# 1. 检查当前版本
fio --version

# 2. 验证优化是否启用
fio --cmdhelp=scramble_buffers

# 3. 对比测试（可选）
# 测试性能差异，验证优化效果
```

**技术背景**: FIO 3.4+版本解决了历史版本中`refill_buffers`导致的性能开销问题，确保测试结果的准确性。

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

### 🛠️ 开发环境设置

```bash
# 1. Fork并克隆项目
git clone https://github.com/your-username/ssd-perf-test.git
cd ssd-perf-test

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 4. 安装pre-commit钩子
pre-commit install
```

### 🔄 提交流程

1. **Fork项目**到您的GitHub账户
2. **创建功能分支**：`git checkout -b feature/amazing-feature`
3. **提交更改**：`git commit -m 'Add amazing feature'`
4. **推送分支**：`git push origin feature/amazing-feature`
5. **创建Pull Request**

### 📝 代码规范

- **Python风格**: 遵循PEP 8规范
- **类型注解**: 添加类型提示
- **文档字符串**: 使用Google风格docstring
- **测试覆盖**: 新功能需要单元测试
- **向后兼容**: 确保API兼容性

### 🧪 测试要求

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 代码覆盖率测试
python3 -m pytest tests/ --cov=ssd_perf_test --cov-report=html

# 代码风格检查
flake8 ssd_perf_test.py tests/
black ssd_perf_test.py tests/
isort ssd_perf_test.py tests/

# 安全性检查
bandit -r ssd_perf_test.py
```

### 🐛 Bug报告

提交Bug报告时，请包含：
- 操作系统和Python版本
- FIO版本信息
- 设备型号和容量
- 错误信息和日志
- 复现步骤

### 💡 功能请求

功能请求请说明：
- 使用场景和需求
- 期望的功能行为
- 实现建议（可选）

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

```
MIT License

Copyright (c) 2024 SSD Performance Test Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 📞 支持与反馈

| 渠道 | 用途 | 链接 |
|------|------|------|
| **问题报告** | Bug反馈和故障排除 | [GitHub Issues](https://github.com/your-username/ssd-perf-test/issues) |
| **功能请求** | 新功能讨论和建议 | [GitHub Discussions](https://github.com/your-username/ssd-perf-test/discussions) |
| **邮件联系** | 私人咨询和合作 | kanshan28@foxmail.com |

## 🔄 更新日志

### 🎉 v2.5.0 (2024-12-16)
- ✨ 新增 `--ramp_time` 参数，自动设置为测试时间的一半
- 🔧 **重要修复**: FIO测试参数配置优化，确保ramp_time参数正确同步
  - 修复测试阶段缺失`--ramp_time`参数的问题
  - 统一预热和测试阶段的参数配置策略
  - 更新FIO命令示例和文档说明
- 🐛 修复设备类型识别问题
- 📊 增强数据稳定性评估（CV分析）
- 🔧 优化参数验证和错误处理
- 📋 新增FIO版本要求详细说明，强调3.4+版本的重要性
- ⚡ 详细说明FIO历史性能问题及优化历程
- 🎨 优化README文档结构，提升GitHub展示效果
- 🔄 **重要更新**: 数据提取从`bw`改为`bw_bytes`，所有性能输出单位从`MiB/s`改为`MB/s`
- 🎯 **核心功能优化**: `_display_performance_conclusions`函数重构，专注CV稳定性评估
  - 移除所有性能数值评估内容
  - 新增CV质量分布统计
  - 增强数据可靠性评级体系

### 📈 v2.4.0
- 🎯 支持64位队列深度配置
- 📈 新增性能等级评估功能
- 🎨 改进终端输出格式

📖 **查看完整的更新历史**: [CHANGELOG.md](CHANGELOG.md)

---

## 🌟 致谢

感谢以下开源项目：
- [FIO](https://github.com/axboe/fio) - 灵活的I/O测试工具
- 所有贡献者和用户的支持

---

> ⚠️ **重要提醒**: 使用本工具进行性能测试时，请确保：
> 1. **备份重要数据**
> 2. **在非生产环境中测试**
> 3. **理解测试对存储设备的影响**
>
> 🚀 **开始您的SSD性能评估之旅！**