#!/usr/bin/env python3
"""
SSD性能测试工具
"""

import os
import sys
import subprocess
import json
import time
import argparse
import csv
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Any


# 全局配置
DEFAULT_TEST_DURATION = 600     # 10分钟标准测试(同时用于预热和测试)
DEFAULT_QUEUE_DEPTH = 32
DEFAULT_THREADS = 4
SCRIPT_VERSION = "2.5.0"

# 测试配置
DATA_VALIDATION_SAMPLES = 3
TEST_RETRY_COUNT = 2

# 单位转换常数
MIB_TO_MBS = 1.048576  # 1 MiB/s = 1.048576 MB/s


# 颜色输出
class Colors:
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    END = '\033[0m'


# 测试结果数据类
class TestResult:
    def __init__(self, test_type: str, block_size: str, rw_pattern: str, 
                 data_points: List, statistics: Dict, evaluation: Dict,
                 execution_time: float, retry_count: int):
        self.test_type = test_type
        self.block_size = block_size
        self.rw_pattern = rw_pattern
        self.data_points = data_points
        self.statistics = statistics
        self.evaluation = evaluation
        self.execution_time = execution_time
        self.retry_count = retry_count


class SSDPerformanceTester:
    """SSD性能测试主类"""
    
    def __init__(self):
        self.device = ""
        self.test_duration = DEFAULT_TEST_DURATION
        self.queue_depth = DEFAULT_QUEUE_DEPTH
        self.threads = DEFAULT_THREADS
        self.debug_mode = False
        self.custom_test_size = ""
        self.result_dir = ""
        self.ramp_time = 0  # 新增ramp_time参数
        # 时间参数
        self.stable_data_start_time = 5
        self.stable_data_end_time = 25
        self.sampling_interval = 5
        
    def log(self, level: str, message: str):
        """简单日志输出"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color = Colors.CYAN if level == "INFO" else Colors.GREEN if level == "SUCCESS" else Colors.YELLOW if level == "WARNING" else Colors.RED
        
        # 在关键步骤之间添加空行以提高可读性
        if level == "INFO" and any(keyword in message for keyword in ["开始执行", "阶段：", "收集系统信息", "测试设备"]):
            print()  # 关键步骤前添加空行
        
        print(f"[{color}{level}{Colors.END}][MainThread] {timestamp} {message}")
        
        # 在错误信息后添加空行
        if level == "ERROR":
            print()  # 仅ERROR级别后添加空行

    def check_device_access(self) -> bool:
        """检查设备访问权限"""
        device_path = f'/dev/{self.device}'
        
        if not os.path.exists(device_path):
            self.log("ERROR", f"设备不存在: {device_path}")
            return False

        try:
            # 简单的FIO测试
            subprocess.run([
                'fio', f'--filename={device_path}', '--rw=read', '--bs=4k',
                '--ioengine=libaio', '--direct=1', '--size=1M', '--runtime=1',
                '--time_based', '--name=test', '--output-format=json'
            ], capture_output=True, timeout=5, check=True)
            return True
        except Exception as e:
            self.log("ERROR", f"设备访问测试失败: {str(e)}")
            return False

    def get_device_type(self, device: str = None) -> str:
        """获取设备类型"""
        if device is None:
            device = self.device
            
        try:
            dev_path = f"/sys/block/{device}"
            if not os.path.exists(dev_path):
                return "unknown"
                
            rotational = 0
            try:
                with open(f"{dev_path}/queue/rotational", 'r') as f:
                    rotational = int(f.read().strip())
            except:
                pass
                
            if device.startswith("nvme"):
                return "nvme"
            elif device.startswith("sd") and rotational == 0:
                return "sata_ssd" 
            elif rotational == 1:
                return "hdd"
            else:
                return "sata_ssd"
                
        except Exception:
            return "unknown"

    def collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        # 获取设备型号和容量信息
        device_model = self._get_device_model()
        device_capacity_gb = self._get_device_capacity_gb()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "device": self.device,
            "device_type": self.get_device_type(),
            "device_model": device_model,
            "device_capacity_gb": device_capacity_gb,
                "test_config": {
                "duration": self.test_duration,
                "ramp_time": self.ramp_time,
                "queue_depth": self.queue_depth,
                "threads": self.threads,
                "test_size": self.custom_test_size or "100%"
            },
            "system": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }

    def _get_device_model(self) -> str:
        """获取设备型号信息"""
        try:
            # 优先使用nvme命令获取信息
            if self.device.startswith("nvme"):
                # 提取控制器名称(如nvme0n1 -> nvme0)
                controller = self.device.rstrip('0123456789')
                if controller == self.device:  # nvme0n1情况
                    controller = ''.join([c for c in self.device if not c.isdigit()])
                    if controller.endswith('n'):
                        controller = controller[:-1]
                
                # 使用nvme list命令获取设备信息
                try:
                    result = subprocess.run(['nvme', 'list'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for i, line in enumerate(lines):
                            if self.device in line and ('LONGSYS' in line or 'Samsung' in line or 'Intel' in line or 'WD' in line):
                                # 查找包含型号信息的行
                                for j in range(max(0, i-2), min(len(lines), i+3)):
                                    if any(brand in lines[j] for brand in ['LONGSYS', 'Samsung', 'Intel', 'WD', 'Kingston', 'Crucial']):
                                        # 提取型号信息
                                        parts = lines[j].split()
                                        for part in parts:
                                            if len(part) > 3 and any(char.isupper() for char in part) and any(char.isdigit() for char in part):
                                                return part
                except:
                    pass
                
                # 备用方案：使用smartctl
                try:
                    result = subprocess.run(['smartctl', '-i', f'/dev/{self.device}'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('Model Number:'):
                                return line.split(':', 1)[1].strip()
                            elif line.startswith('Device Model:'):
                                return line.split(':', 1)[1].strip()
                except:
                    pass
            else:
                # SATA设备使用hdparm或smartctl
                try:
                    result = subprocess.run(['hdparm', '-I', f'/dev/{self.device}'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Model Number:' in line:
                                return line.split('Model Number:')[1].strip()
                except:
                    pass
                
                try:
                    result = subprocess.run(['smartctl', '-i', f'/dev/{self.device}'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if line.startswith('Device Model:'):
                                return line.split(':', 1)[1].strip()
                            elif line.startswith('Model Number:'):
                                return line.split(':', 1)[1].strip()
                except:
                    pass
                    
        except Exception:
            pass
            
        return "Unknown"
    
    def _get_device_capacity_gb(self) -> float:
        """获取设备容量(GB)"""
        try:
            # 优先使用nvme命令获取精确容量
            if self.device.startswith("nvme"):
                try:
                    result = subprocess.run(['nvme', 'list'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if self.device in line and 'TB' in line:
                                # 解析容量信息,如 "3.20 TB"
                                import re
                                match = re.search(r'(\d+\.?\d*)\s*(TB|GB)', line)
                                if match:
                                    size = float(match.group(1))
                                    unit = match.group(2)
                                    if unit == 'TB':
                                        return size * 1024
                                    else:
                                        return size
                except:
                    pass
                
                # 备用方案：使用smartctl获取容量
                try:
                    result = subprocess.run(['smartctl', '-i', f'/dev/{self.device}'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'Total NVM Capacity:' in line or 'user capacity:' in line.lower():
                                # 解析容量信息,如 "3,200,631,791,616 [3.20 TB]"
                                import re
                                # 查找TB或GB数值
                                tb_match = re.search(r'\[(\d+\.?\d*)\s*TB\]', line)
                                gb_match = re.search(r'\[(\d+\.?\d*)\s*GB\]', line)
                                
                                if tb_match:
                                    return float(tb_match.group(1)) * 1024
                                elif gb_match:
                                    return float(gb_match.group(1))
                except:
                    pass
            else:
                # SATA设备容量获取
                try:
                    result = subprocess.run(['blockdev', '--getsize64', f'/dev/{self.device}'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        size_bytes = int(result.stdout.strip())
                        return size_bytes / (1024**3)  # 转换为GB
                except:
                    pass
                    
        except Exception:
            pass
            
        return 0.0
    
    def _execute_single_test(self, test_type: str, block_size: str, rw_pattern: str, 
                           queue_depth: int = None, numjobs: int = None, sample_id: int = 0) -> TestResult:
        """执行单次测试"""
        output_prefix = f"{test_type}_{block_size}_{rw_pattern}"
        if sample_id > 0:
            output_prefix += f"_sample{sample_id}"
            
        output_json = os.path.join(self.result_dir, f"{output_prefix}.json")
        
        # 使用指定的队列深度和任务数,如果没有指定则使用默认值
        test_queue_depth = queue_depth if queue_depth is not None else self.queue_depth
        test_numjobs = numjobs if numjobs is not None else self.threads
        
        # 构建FIO命令
        # 如果用户通过 --size 指定了测试大小，则优先使用；否则默认 100%
        fio_size = self.custom_test_size or "100%"
        fio_cmd = [
            "fio",
            f"--name={output_prefix}",
            f"--filename=/dev/{self.device}",
            "--ioengine=libaio",
            "--direct=1",
            f"--numjobs={test_numjobs}",
            f"--iodepth={test_queue_depth}",
            f"--rw={rw_pattern}",
            f"--bs={block_size}",
            f"--runtime={self.test_duration}",
            f"--ramp_time={self.ramp_time}",
            "--time_based=1",
            f"--size={fio_size}",
            "--refill_buffers",
            "--end_fsync=1",
            "--norandommap=1",
            "--randrepeat=0",
            "--group_reporting",
            "--output-format=json",
            f"--output={output_json}"
        ]
        
        # 只在第一次采样时打印完整命令
        if sample_id == 0:
            cmd_str = ' '.join(fio_cmd)
            self.log("INFO", f"FIO命令: {cmd_str}")
        
        # 执行命令
        start_time = time.time()
        result = subprocess.run(fio_cmd, capture_output=True, text=True)
        execution_time = time.time() - start_time
        
        if result.returncode != 0:
            error_msg = f"命令执行失败 (返回码: {result.returncode})"
            # 尽可能把 FIO 的 stderr/stdout 关键信息打到日志里，方便排查问题
            stderr_preview = (result.stderr or "").strip()
            stdout_preview = (result.stdout or "").strip()
            if stderr_preview:
                self.log("ERROR", f"FIO stderr: {stderr_preview[:800]}")
            if stdout_preview:
                self.log("ERROR", f"FIO stdout: {stdout_preview[:400]}")
            self.log("ERROR", f"=== 命令执行失败详情 ===")
            raise Exception(error_msg)
        
        # 加载和验证结果
        json_data = self._load_and_validate_json(output_json)
        if not json_data:
            raise Exception("结果文件无效或为空")
            
        # 调试：打印JSON结构
        if self.debug_mode and sample_id == 0:
            print(f"调试: JSON数据结构={json.dumps(json_data, indent=2)[:1000]}...")
            print(f"调试: job options={json_data.get('jobs', [{}])[0].get('job options', {})}")
        
        # 提取性能指标
        metrics = self._extract_performance_metrics({
            "json_data": json_data,
            "job_name": output_prefix,
            "execution_time": execution_time
        })
        
        # 创建测试结果
        test_result = TestResult(
            test_type=test_type,
            block_size=block_size,
            rw_pattern=rw_pattern,
            data_points=[],
            statistics={},
            evaluation={},
            execution_time=execution_time,
            retry_count=0
        )
        
        # 填充统计数据
        test_result.statistics = {
            "mean": metrics.get("primary_metric", 0),
            "execution_time": execution_time
        }
        
        # 数据质量评估
        test_result.evaluation = self._evaluate_test_result(test_result)
        
        return test_result
    
    def _load_and_validate_json(self, json_file: str) -> Optional[Dict]:
        """加载并验证JSON文件"""
        if not os.path.exists(json_file) or os.path.getsize(json_file) < 100:
            return None
            
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
            
            if "jobs" not in data or not data["jobs"]:
                return None
                
            return data
        except json.JSONDecodeError:
            return None
    
    def _extract_performance_metrics(self, test_result: Dict) -> Dict[str, float]:
        """提取性能指标"""
        json_data = test_result["json_data"]
        
        if not json_data or "jobs" not in json_data or not json_data["jobs"]:
            return {}
            
        job = json_data["jobs"][0]
        
        # 尝试从多个地方获取读写模式
        rw_mode = job.get("rw", "")
        if not rw_mode:
            # 从job options中获取
            job_options = job.get("job options", {})
            rw_mode = job_options.get("rw", "")
        
        # 如果还是没有,从job_name推断
        if not rw_mode:
            job_name = job.get("jobname", "")
            if "write" in job_name:
                rw_mode = "write"
            elif "read" in job_name:
                rw_mode = "read"
            else:
                # 默认假设为写入
                rw_mode = "write"
        
        # 获取读/写数据
        read_data = job.get("read", {})
        write_data = job.get("write", {})
        
        # 调试信息
        if self.debug_mode:
            print(f"调试: rw模式={rw_mode}")
            print(f"调试: job name={job.get('jobname', '')}")
            print(f"调试: read io_bytes={read_data.get('io_bytes', 0)}, write io_bytes={write_data.get('io_bytes', 0)}")
        
        # 从bw_bytes提取并转换为MB/s (1 MiB/s = 1.048576 MB/s)
        # bw_bytes单位是bytes/sec，需要转换为MB/s: bytes/sec / 1024^2 = MiB/s，再转换为MB/s
        read_bw_mib = read_data.get("bw_bytes", 0) / (1024 * 1024)  # 转换为MiB/s
        write_bw_mib = write_data.get("bw_bytes", 0) / (1024 * 1024)  # 转换为MiB/s
        read_bw_mbs = read_bw_mib * MIB_TO_MBS  # 转换为MB/s
        write_bw_mbs = write_bw_mib * MIB_TO_MBS  # 转换为MB/s
        
        # 根据实际的数据来判断读写模式,而不是依赖rw字段
        read_io_bytes = read_data.get("io_bytes", 0)
        write_io_bytes = write_data.get("io_bytes", 0)
        
        # 如果有读数据,则使用读性能；否则使用写性能
        if read_io_bytes > 0:
            if "rand" in rw_mode or job.get("jobname", "").startswith("random"):
                primary_metric = read_data.get("iops", 0)  # 随机读用IOPS
            else:
                primary_metric = read_bw_mbs  # 顺序读用带宽(MB/s)
        else:
            if "rand" in rw_mode or job.get("jobname", "").startswith("random"):
                primary_metric = write_data.get("iops", 0)  # 随机写用IOPS
            else:
                primary_metric = write_bw_mbs  # 顺序写用带宽(MB/s)
        
        # 调试信息
        if self.debug_mode:
            print(f"调试: 主要指标={primary_metric}")
            print(f"调试: read_bw={read_bw_mbs:.2f} MB/s, read_iops={read_data.get('iops', 0)}")
            print(f"调试: write_bw={write_bw_mbs:.2f} MB/s, write_iops={write_data.get('iops', 0)}")
            
        return {
            "read_bw": read_bw_mbs,
            "read_iops": read_data.get("iops", 0),
            "read_lat": read_data.get("lat_ns", {}).get("mean", 0) / 1000,
            "write_bw": write_bw_mbs,
            "write_iops": write_data.get("iops", 0),
            "write_lat": write_data.get("lat_ns", {}).get("mean", 0) / 1000,
            "primary_metric": primary_metric,
            "execution_time": test_result.get("execution_time", 0)
        }
    
    def _evaluate_test_result(self, result: TestResult) -> Dict[str, Any]:
        """评估测试结果质量"""
        evaluation = {
            "status": "SUCCESS",
            "data_quality": "GOOD",
            "notes": []
        }
        
        # 只评估数据质量,不进行性能等级评价
        return evaluation
    
    def retry_operation(self, operation, operation_name: str):
        """重试机制"""
        last_error = None
        for attempt in range(TEST_RETRY_COUNT + 1):
            try:
                return operation()
            except Exception as e:
                last_error = e
                if attempt < TEST_RETRY_COUNT:
                    self.log("WARNING", f"{operation_name} 重试 {attempt + 1}/{TEST_RETRY_COUNT}: {str(e)}")
                    time.sleep(1)
        
        raise last_error
    
    def run_enhanced_test(self, test_type: str, block_size: str, rw_pattern: str, 
                         queue_depth: int = None, numjobs: int = None) -> TestResult:
        """运行增强测试(多次采样)"""
        self.log("INFO", f"开始增强测试: {test_type}_{block_size}_{rw_pattern} (QD:{queue_depth or self.queue_depth}, Jobs:{numjobs or self.threads})")
        
        # 执行多次采样
        results = []
        for sample_id in range(DATA_VALIDATION_SAMPLES):
            try:
                result = self.retry_operation(
                    lambda: self._execute_single_test(test_type, block_size, rw_pattern, queue_depth, numjobs, sample_id),
                    f"FIO测试-{test_type}_{block_size}_{rw_pattern}"
                )
                results.append(result)

            except Exception as e:
                self.log("ERROR", f"测试失败: {str(e)}")
                # 创建失败结果
                failed_result = TestResult(
                    test_type=test_type,
                    block_size=block_size,
                    rw_pattern=rw_pattern,
                    data_points=[],
                    statistics={},
                    evaluation={"status": "FAILED", "error": str(e)},
                    execution_time=0,
                    retry_count=TEST_RETRY_COUNT
                )
                results.append(failed_result)
        
        # 合并结果
        if results:
            return self._merge_test_results(results, test_type, block_size, rw_pattern)
        else:
            raise Exception("所有采样均失败")
    
    def _merge_test_results(self, results: List[TestResult], test_type: str, block_size: str, rw_pattern: str) -> TestResult:
        """合并多次测试结果"""
        valid_results = [r for r in results if r.evaluation.get("status") != "FAILED"]
        
        if not valid_results:
            return results[0]  # 返回第一个失败结果
        
        # 计算统计指标
        primary_metrics = [r.statistics.get("mean", 0) for r in valid_results]
        execution_times = [r.execution_time for r in valid_results]
        
        mean_value = statistics.mean(primary_metrics) if primary_metrics else 0
        stdev_value = statistics.stdev(primary_metrics) if len(primary_metrics) > 1 else 0
        cv = stdev_value / mean_value if mean_value > 0 else float('inf')  # 变异系数：标准差/均值
        
        # 创建合并结果
        merged_result = TestResult(
            test_type=test_type,
            block_size=block_size,
            rw_pattern=rw_pattern,
            data_points=[],
            statistics={
                "mean": mean_value,
                "stdev": stdev_value,
                "cv": cv,
                "min": min(primary_metrics) if primary_metrics else 0,
                "max": max(primary_metrics) if primary_metrics else 0,
                "sample_count": len(valid_results),
                "execution_time_mean": statistics.mean(execution_times) if execution_times else 0
            },
            evaluation={},
            execution_time=statistics.mean(execution_times) if execution_times else 0,
            retry_count=sum(r.retry_count for r in results)
        )
        
        # 评估合并结果
        merged_result.evaluation = self._evaluate_test_result(merged_result)
        
        # 数据质量评估(基于变异系数CV)
        if cv < 0.1:  # CV<0.1: 数据稳定性极好
            merged_result.evaluation["data_quality"] = "EXCELLENT"
        elif cv < 0.2:  # CV<0.2: 数据稳定性良好
            merged_result.evaluation["data_quality"] = "GOOD"
        else:  # CV>0.2: 数据波动较大
            merged_result.evaluation["data_quality"] = "POOR"
            merged_result.evaluation["notes"].append(f"数据波动较大,变异系数{cv:.3f}")
        
        return merged_result
    
    def run_comprehensive_test(self) -> List[TestResult]:
        """运行综合性能测试 - 优化数据写入策略"""
        results = []
        
        # 定义测试配置 - 按照1)顺序写 2)顺序读 3)随机写 4)随机读的顺序
        test_configs = [
            {"test_type": "sequential", "block_size": "128k", "rw_pattern": "write", "queue_depth": 128, "numjobs": 1, "stage": "第二阶段：128K顺序写入/QD128/Job1"},
            {"test_type": "sequential", "block_size": "128k", "rw_pattern": "read", "queue_depth": 128, "numjobs": 1, "stage": "第三阶段：128K顺序读取/QD128/Job1"},
            {"test_type": "random", "block_size": "4k", "rw_pattern": "write", "queue_depth": 32, "numjobs": 8, "stage": "第五阶段：4K随机写入/QD32/Job8"},
            {"test_type": "random", "block_size": "4k", "rw_pattern": "read", "queue_depth": 32, "numjobs": 8, "stage": "第六阶段：4K随机读取/QD32/Job8"}
        ]
        
        total_tests = len(test_configs)
        self.log("INFO", f"开始执行优化版SSD性能测试流程 {total_tests} 个测试用例...")

        # 第一步：顺序写预热(使用ramp_time参数)
        warmup_time = self.ramp_time  # 使用ramp_time参数
        self.log("INFO", f"第一阶段：顺序写预热{warmup_time}秒 [QD128/Job1]")
        warmup_size = self.custom_test_size or "100%"
        try:
            seq_warmup_cmd = ["fio", "--name=seq_warmup", f"--filename=/dev/{self.device}",
                              "--rw=write", "--bs=128k", "--ioengine=libaio", "--direct=1",
                              "--numjobs=1", "--iodepth=128", f"--runtime={warmup_time}", "--time_based=1",
                              f"--size={warmup_size}", "--refill_buffers", "--end_fsync=1", 
                              "--norandommap=1", "--randrepeat=0", "--group_reporting",
                              "--output-format=json", "--output=/tmp/seq_warmup.json"]
            
            subprocess.run(seq_warmup_cmd, capture_output=True, check=False)
            self.log("SUCCESS", "顺序写预热完成")
        except Exception as e:
            self.log("WARNING", f"顺序写预热失败,继续测试: {str(e)}")

        # 执行测试循环
        for i, config in enumerate(test_configs, 1):
            test_type = config["test_type"]
            block_size = config["block_size"] 
            rw_pattern = config["rw_pattern"]
            queue_depth = config["queue_depth"]
            numjobs = config["numjobs"]
            stage = config["stage"]
            
            # 特殊处理：第四步随机写预热(使用ramp_time参数)
            if i == 3:  # 在随机写测试前进行预热
                warmup_time = self.ramp_time  # 使用ramp_time参数
                self.log("INFO", f"第四阶段：随机写预热{warmup_time}秒 [QD32/Job8]")
                warmup_size = self.custom_test_size or "100%"
                try:
                    rand_warmup_cmd = ["fio", "--name=rand_warmup", f"--filename=/dev/{self.device}",
                                      "--rw=randwrite", "--bs=4k", "--ioengine=libaio", "--direct=1",
                                      "--numjobs=8", "--iodepth=32", f"--runtime={warmup_time}", "--time_based=1",
                                      f"--size={warmup_size}", "--refill_buffers", "--end_fsync=1",
                                      "--norandommap=1", "--randrepeat=0", "--group_reporting",
                                      "--output-format=json", "--output=/tmp/rand_warmup.json"]
                    
                    subprocess.run(rand_warmup_cmd, capture_output=True, check=False)
                    self.log("SUCCESS", "随机写预热完成")
                except Exception as e:
                    self.log("WARNING", f"随机写预热失败,继续测试: {str(e)}")

            self.log("INFO", f"执行测试 {i+1}/{total_tests+1}: {test_type} {block_size} {rw_pattern} [{stage}]")
            self.log("INFO", f"参数配置: 队列深度={queue_depth}, 任务数={numjobs}")

            try:
                result = self.run_enhanced_test(test_type, block_size, rw_pattern, queue_depth, numjobs)
                results.append(result)

                # 显示性能结果
                mean_value = result.statistics.get("mean", 0)
                # 使用明确的类型判断，避免字符串包含关系产生歧义
                if result.test_type == "sequential":
                    performance_str = f"{mean_value:.2f} MB/s"
                else:
                    performance_str = f"{mean_value:.0f} IOPS"

                cv = result.statistics.get("cv", 0)  # 变异系数：衡量数据稳定性
                self.log("SUCCESS", f"测试完成 - 性能: {performance_str}, CV: {cv:.3f}")

            except Exception as e:
                self.log("ERROR", f"测试执行失败: {str(e)}")
                # 创建失败结果
                failed_result = TestResult(
                    test_type=test_type,
                    block_size=block_size,
                    rw_pattern=rw_pattern,
                    data_points=[],
                    statistics={},
                    evaluation={"status": "FAILED", "error": str(e)},
                    execution_time=0,
                    retry_count=TEST_RETRY_COUNT
                )
                results.append(failed_result)
        
        return results
    
    def save_results(self, results: List[TestResult], system_info: Dict):
        """保存测试结果"""
        # CSV报告
        csv_file = os.path.join(self.result_dir, "performance_report.csv")
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
            "测试类型", "块大小", "读写模式", "主要指标", "均值", "标准差", "变异系数",
            "执行时间", "重试次数"
            ])
            
            for result in results:
                # 确定正确的单位
                if result.test_type == "sequential":
                    unit = "MB/s"
                    format_str = f"{result.statistics.get('mean', 0):.2f}"
                else:
                    unit = "IOPS"
                    format_str = f"{result.statistics.get('mean', 0):.0f}"
                
                writer.writerow([
                    result.test_type,
                    result.block_size,
                    result.rw_pattern,
                    unit,
                    format_str,
                    f"{result.statistics.get('stdev', 0):.2f}",
                    f"{result.statistics.get('cv', 0):.3f}",
                    f"{result.execution_time:.2f}",
                    result.retry_count
                ])

        # JSON报告
        json_file = os.path.join(self.result_dir, "performance_report.json")
        report_data = {
            "version": SCRIPT_VERSION,
            "timestamp": datetime.now().isoformat(),
            "system_info": system_info,
            "test_results": []
        }
        
        for result in results:
            result_dict = {
                "test_type": result.test_type,
                "block_size": result.block_size,
                "rw_pattern": result.rw_pattern,
                "statistics": result.statistics,
                "evaluation": result.evaluation,
                "execution_time": result.execution_time,
                "retry_count": result.retry_count
            }
            report_data["test_results"].append(result_dict)

        with open(json_file, "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # 系统信息
        sysinfo_file = os.path.join(self.result_dir, "system_info.txt")
        with open(sysinfo_file, "w") as f:
            f.write(f"测试时间: {system_info.get('timestamp', 'Unknown')}\n")
            f.write(f"设备: {system_info.get('device', 'Unknown')}\n")
            f.write(f"设备类型: {system_info.get('device_type', 'Unknown')}\n")
            f.write(f"设备型号: {system_info.get('device_model', 'Unknown')}\n")
            f.write(f"设备容量: {system_info.get('device_capacity_gb', 0):.1f} GB\n")
            f.write(f"测试配置:\n")
            for key, value in system_info.get('test_config', {}).items():
                f.write(f"  {key}: {value}\n")
            
            f.write(f"\n系统信息:\n")
            for key, value in system_info.get('system', {}).items():
                f.write(f"  {key}: {value}\n")
        
        self.log("INFO", f"结果已保存到目录: {self.result_dir}")
    
    def parse_arguments(self) -> bool:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description="SSD性能测试脚本 (修复版本)", add_help=False)
        parser.add_argument("device", nargs="?", help="要测试的设备名 (如: sda, nvme0n1)")
        parser.add_argument("-t", "--time", type=int, default=DEFAULT_TEST_DURATION, help=f"预热和测试持续时间 (默认: {DEFAULT_TEST_DURATION}秒)")
        parser.add_argument("-q", "--queue", type=int, default=DEFAULT_QUEUE_DEPTH, help=f"队列深度 (默认: {DEFAULT_QUEUE_DEPTH})")
        parser.add_argument("-j", "--jobs", type=int, default=DEFAULT_THREADS, help=f"并发线程数 (默认: {DEFAULT_THREADS})")
        parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")
        parser.add_argument("--size", type=str, metavar="SIZE", help="自定义测试大小 (例如: 10G, 500M, 20%, 100%)")
        parser.add_argument("--ramp_time", type=int, help=f"预热时间 (默认: 自动设置为-t参数值的一半)")
        parser.add_argument("-h", "--help", action="store_true", help="显示帮助信息")
        
        try:
            # argparse 在解析错误时会调用 sys.exit，这里捕获 SystemExit，
            # 统一打印帮助信息并返回 False，避免脚本直接退出
            args = parser.parse_args()
        except SystemExit:
            self.show_help()
            return False
        
        if args.help or not args.device:
            self.show_help()
            return False
        
        self.device = args.device
        self.test_duration = args.time
        
        # 验证测试时间参数
        if self.test_duration <= 0:
            self.log("ERROR", "测试时间必须大于0秒")
            return False
        
        # 设置ramp_time参数
        if args.ramp_time is not None:
            if args.ramp_time < 0:
                self.log("ERROR", "ramp_time不能为负数")
                return False
            elif args.ramp_time >= self.test_duration:
                self.log("ERROR", "ramp_time不能大于或等于测试时间")
                return False
            self.ramp_time = args.ramp_time
        else:
            # 自动设置为-t参数值的一半
            self.ramp_time = self.test_duration // 2
        
        self.queue_depth = args.queue
        self.threads = args.jobs
        self.debug_mode = args.debug
        self.custom_test_size = getattr(args, 'size', "")
        
        return True
    
    def show_help(self) -> None:
        """显示帮助信息"""
        help_text = f"""
SSD性能测试脚本 v{SCRIPT_VERSION} (修复版本)

用法:
    python ssd_perf_test.py [选项] <设备名>

建议的测试命令:
    python3 ssd_perf_test.py nvme0n1 --debug

必需参数:
    <设备名>         要测试的SSD设备名 (如: sda, nvme0n1)

可选参数:
    -t, --time      预热和测试持续时间 (默认: {DEFAULT_TEST_DURATION}秒)
    -q, --queue     队列深度 (默认: {DEFAULT_QUEUE_DEPTH})
    -j, --jobs      并发线程数 (默认: {DEFAULT_THREADS})
    -d, --debug     启用调试模式
    --size          自定义测试大小 (默认: 100%,例如: 10G, 500M, 20%, 100%)
    --ramp_time     预热时间 (默认: 自动设置为-t参数值的一半)
    -h, --help      显示此帮助信息

=== 优化版测试流程 ===

1. 顺序写预热 (使用--ramp_time参数指定时间, 默认为-t参数值的一半, QD128/Job1)
2. 128K顺序写入测试 (使用-t参数指定时间, 默认10分钟, 队列深度:128, 任务数:1)
3. 128K顺序读取测试 (使用-t参数指定时间, 默认10分钟, 队列深度:128, 任务数:1)
4. 随机写预热 (使用--ramp_time参数指定时间, 默认为-t参数值的一半, QD32/Job8)
5. 4K随机写入测试 (使用-t参数指定时间, 默认10分钟, 队列深度:32, 任务数:8)
6. 4K随机读取测试 (使用-t参数指定时间, 默认10分钟, 队列深度:32, 任务数:8)

总执行时间: 预热时间(默认20分钟) + 测试时间 (默认40分钟)

预热策略说明:
• 顺序写预热使用与顺序写完全相同的参数配置 (QD128/Job1)
• 随机写预热使用与随机写完全相同的参数配置 (QD32/Job8)
• --ramp_time参数默认自动设置为-t参数值的一半,也可手动指定

测试模型说明:
• 128K顺序读/QD128/Job1 - 大文件顺序读写性能 (MB/s)
• 128K顺序写/QD128/Job1 - 大文件顺序写入性能 (MB/s)
• 4K随机读/QD32/Job8 - 小文件随机读取性能 (IOPS)
• 4K随机写/QD32/Job8 - 小文件随机写入性能 (IOPS)

FIO命令示例(128K顺序写入):
fio --name=sequential_128k_write --filename=/dev/nvme0n1 --ioengine=libaio --direct=1 --numjobs=1 --iodepth=128 --rw=write --bs=128k --runtime=30 --ramp_time=15 --time_based=1 --size=100% --refill_buffers --end_fsync=1 --norandommap=1 --randrepeat=0 --group_reporting --output-format=json --output=sequential_128k_write.json

变异系数(CV)说明:
• CV < 0.1: 数据稳定性极好(标准差/均值 < 10%)
• CV < 0.2: 数据稳定性良好(标准差/均值 < 20%)  
• CV > 0.2: 数据波动较大(标准差/均值 > 20%)

输出文件:
• performance_report.csv  - CSV格式性能报告
• performance_report.json - JSON格式详细报告  
• system_info.txt        - 系统信息和测试配置

更新内容:
• 实现4种标准SSD性能测试模型
• 为每种测试模式配置专用参数
• 增强测试配置显示
• 添加数据稳定性评估(变异系数)
• 新增--ramp_time参数,默认自动设置为-t参数值的一半
• 支持自定义预热时间,优化测试流程
"""
        print(help_text)
    
    def show_summary(self, results: List[TestResult]):
        """显示测试总结"""
        self._display_detailed_summary(results)
        
    def _display_detailed_summary(self, results: List[TestResult]):
        """显示详细测试总结,包含CV分析和性能评估"""
        successful_tests = [r for r in results if r.evaluation.get("status") != "FAILED"]
        failed_tests = [r for r in results if r.evaluation.get("status") == "FAILED"]
        
        # 计算整体统计数据
        overall_cv_analysis = self._calculate_overall_cv_analysis(successful_tests)
        performance_summary = self._generate_performance_summary(successful_tests)
        
        # 显示测试概览
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}SSD性能测试完整评估报告{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        
        # 基本统计信息
        print(f"\n{Colors.BOLD}📊 测试概览{Colors.END}")
        print(f"总测试数: {len(results)}")
        print(f"成功测试: {Colors.GREEN}{len(successful_tests)}{Colors.END}")
        print(f"失败测试: {Colors.RED}{len(failed_tests)}{Colors.END}")
        print(f"测试通过率: {Colors.GREEN}{len(successful_tests)/len(results)*100:.1f}%{Colors.END}" if results else "0.0%")

        # CV稳定性分析
        self._display_cv_analysis(overall_cv_analysis)

        # 性能数据详情
        self._display_performance_details(successful_tests)

        # 性能评估结论
        self._display_performance_conclusions(performance_summary, overall_cv_analysis)
        
        # 失败测试信息
        if failed_tests:
            self._display_failed_tests(failed_tests)
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    
    def _calculate_overall_cv_analysis(self, successful_tests: List[TestResult]) -> Dict[str, Any]:
        """计算整体CV分析数据"""
        if not successful_tests:
            return {"avg_cv": 0, "min_cv": 0, "max_cv": 0, "stability_rating": "无数据"}
        
        cv_values = [r.statistics.get("cv", 0) for r in successful_tests]
        avg_cv = sum(cv_values) / len(cv_values)
        min_cv = min(cv_values)
        max_cv = max(cv_values)
        
        # 稳定性评级
        if avg_cv < 0.05:
            stability_rating = "卓越 (CV<0.05)"
        elif avg_cv < 0.1:
            stability_rating = "极好 (CV<0.1)"
        elif avg_cv < 0.2:
            stability_rating = "良好 (CV<0.2)"
        else:
            stability_rating = "需改进 (CV>0.2)"
            
        return {
            "avg_cv": avg_cv,
            "min_cv": min_cv,
            "max_cv": max_cv,
            "stability_rating": stability_rating,
            "cv_values": cv_values
        }
    
    def _generate_performance_summary(self, successful_tests: List[TestResult]) -> Dict[str, Any]:
        """生成性能摘要"""
        summary = {
            "sequential_write": None,
            "sequential_read": None,
            "random_write": None,
            "random_read": None
        }
        
        for result in successful_tests:
            test_key = f"{result.test_type}_{result.rw_pattern}"
            mean_value = result.statistics.get("mean", 0)
            
            if test_key == "sequential_write":
                summary["sequential_write"] = mean_value
            elif test_key == "sequential_read":
                summary["sequential_read"] = mean_value
            elif test_key == "random_write":
                summary["random_write"] = mean_value
            elif test_key == "random_read":
                summary["random_read"] = mean_value
                
        return summary
    
    def _display_cv_analysis(self, cv_analysis: Dict[str, Any]):
        """显示CV分析结果"""
        print(f"\n{Colors.BOLD}📈 变异系数(CV)稳定性分析{Colors.END}")
        print(f"平均CV值: {cv_analysis['avg_cv']:.3f} ({cv_analysis['avg_cv']*100:.1f}%)")
        print(f"CV范围: {cv_analysis['min_cv']:.3f} ~ {cv_analysis['max_cv']:.3f}")
        print(f"稳定性评级: {Colors.GREEN}{cv_analysis['stability_rating']}{Colors.END}")
        
        # CV解释说明
        if cv_analysis['avg_cv'] < 0.1:
            print(f"💡 {Colors.GREEN}结论: 数据稳定性极好,测试结果高度可靠{Colors.END}")
        else:
            print(f"⚠️  {Colors.YELLOW}注意: 数据存在一定波动,建议多次测试验证{Colors.END}")

    def _display_performance_details(self, successful_tests: List[TestResult]):
        """显示性能数据详情"""
        print(f"\n{Colors.BOLD}⚡ 详细性能数据{Colors.END}")
        
        for result in successful_tests:
            test_name = f"{result.test_type} {result.block_size} {result.rw_pattern}"
            mean_value = result.statistics.get("mean", 0)
            cv = result.statistics.get("cv", 0)
            quality = result.evaluation.get("data_quality", "UNKNOWN")
            
            # 根据测试类型确定格式和单位
            if "seq" in result.test_type:
                mean_str = f"{mean_value:.2f} MB/s"
                icon = "📁" if result.rw_pattern == "write" else "📖"
            else:
                mean_str = f"{mean_value:,.0f} IOPS"
                icon = "✏️" if result.rw_pattern == "write" else "🔍"
            
            # 质量评级颜色
            quality_color = Colors.GREEN if quality == "EXCELLENT" else Colors.YELLOW if quality == "GOOD" else Colors.RED
            
            print(f"  {icon} {test_name}:")
            print(f"     性能: {Colors.BOLD}{mean_str}{Colors.END}")
            print(f"     CV: {cv:.3f} | 质量: {quality_color}{quality}{Colors.END}")

    def _display_performance_conclusions(self, performance_summary: Dict[str, Any], cv_analysis: Dict[str, Any]):
        """显示基于CV的性能评估结论"""
        print(f"\n{Colors.BOLD}🎯 数据稳定性评估结论{Colors.END}")
        
        # 基于CV稳定性的综合评价
        if cv_analysis['avg_cv'] < 0.01:
            stability_desc = "数据极其稳定"
            reliability = "极高"
            recommendation = "测试结果高度可靠，可用于重要性能评估"
        elif cv_analysis['avg_cv'] < 0.05:
            stability_desc = "数据高度稳定" 
            reliability = "很高"
            recommendation = "测试结果可靠，建议作为基准性能参考"
        elif cv_analysis['avg_cv'] < 0.1:
            stability_desc = "数据稳定性优秀"
            reliability = "高"
            recommendation = "测试结果较为可靠，适合一般性能评估"
        else:
            stability_desc = "数据存在波动"
            reliability = "中等"
            recommendation = "建议增加测试次数以获得更稳定的结果"
        
        print(f"  🔍 稳定性: {stability_desc} (平均CV: {cv_analysis['avg_cv']:.3f})")
        print(f"  🎯 可靠性: {reliability}")
        print(f"  💡 建议: {recommendation}")
        
        # CV质量分布统计
        cv_values = cv_analysis.get('cv_values', [])
        if cv_values:
            excellent_count = sum(1 for cv in cv_values if cv < 0.05)
            good_count = sum(1 for cv in cv_values if 0.05 <= cv < 0.1)
            poor_count = sum(1 for cv in cv_values if cv >= 0.1)
            
            print(f"\n{Colors.BOLD}📊 CV质量分布{Colors.END}")
            print(f"  优秀(CV<0.05): {excellent_count}/{len(cv_values)} 项测试")
            print(f"  良好(0.05≤CV<0.1): {good_count}/{len(cv_values)} 项测试")
            print(f"  波动较大(CV≥0.1): {poor_count}/{len(cv_values)} 项测试")

    def _display_failed_tests(self, failed_tests: List[TestResult]):
        """显示失败测试信息"""
        print(f"\n{Colors.BOLD}❌ 失败测试详情{Colors.END}")
        for result in failed_tests:
            test_name = f"{result.test_type} {result.block_size} {result.rw_pattern}"
            error = result.evaluation.get("error", "Unknown error")
            print(f"  {Colors.RED}{test_name}: {error}{Colors.END}")
    
    def _update_time_parameters(self):
        """更新时间参数"""
        self.stable_data_start_time = min(5, self.test_duration * 0.1)
        self.stable_data_end_time = min(self.test_duration - 5, self.test_duration * 0.9)
        self.sampling_interval = max(1, (self.stable_data_end_time - self.stable_data_start_time) / 4)
    
    def set_default_params(self, device: str):
        """根据设备类型设置默认参数"""
        device_type = self.get_device_type(device)
        
        if device_type == "nvme":
            self.queue_depth = max(self.queue_depth, 64)
            self.threads = max(self.threads, 4)
        elif device_type == "sata_ssd":
            self.queue_depth = max(self.queue_depth, 32)
            self.threads = max(self.threads, 2)
        else:  # hdd or unknown
            self.queue_depth = min(self.queue_depth, 16)
            self.threads = min(self.threads, 2)
    
    def run(self) -> bool:
        """主执行函数"""
        if not self.parse_arguments():
            return False
            
        # 设备访问检查
        if not self.check_device_access():
            return False
            
        # 创建结果目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.result_dir = f"results_{self.device}_{timestamp}"
        os.makedirs(self.result_dir, exist_ok=True)
        
        self.log("INFO", f"结果目录: {self.result_dir}")

        # 更新时间参数
        self._update_time_parameters()

        # 根据设备类型设置默认参数
        self.set_default_params(self.device)

        # 收集系统信息
        self.log("INFO", "收集系统信息...")
        system_info = self.collect_system_info()

        # 显示测试配置
        self.log("INFO", f"测试设备: {self.device} ({system_info.get('device_model', 'Unknown')}, {system_info.get('device_capacity_gb', 0):.1f} GB)")
        self.log("INFO", f"设备类型: {system_info.get('device_type', 'Unknown')}")
        self.log("INFO", f"测试时间: {self.test_duration}秒, 预热时间: {self.ramp_time}秒")

        # 运行测试
        try:
            results = self.run_comprehensive_test()

            # 保存结果
            self.save_results(results, system_info)

            # 显示总结
            self.show_summary(results)

            return True

        except KeyboardInterrupt:
            self.log("WARNING", "测试被用户中断")
            return False
        except Exception as e:
            self.log("ERROR", f"测试执行失败: {str(e)}")
            return False

def main():
    tester = SSDPerformanceTester()
    success = tester.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()