import re 
import argparse

# 创建解析器对象
parser = argparse.ArgumentParser(description='从rclone日志中提取md5校验和的脚本')

parser.add_argument('-i', '--input-file', type=str, default='rclone.log', help='输入日志对应路径，默认为 ./rclone.log')

parser.add_argument('-o', '--output-file', type=str, default='MD5SUMs.txt', help='输入日志对应路径，默认为 ./MD5SUMs.txt')
# 解析命令行参数
args = parser.parse_args()
# 请根据你的实际日志文件路径修改下面的路径 
log_file_path = args.input_file 
checksum_file_path = args.output_file
# 正则表达式，用于从日志中匹配 MD5 校验和和文件名 
# 假设日志中的行格式为 "MD5 hash of file.txt: 12345abcdef67890" 
checksum_pattern = re.compile(r'DEBUG : ([^:]+): (md|MD)5 = ([a-fA-F0-9]{32})') # DEBUG : idb/edfexport/Settings/Icu/ICU Waveforms.wks: md5 = 677975de6a15e03d0b88216d2b267c51 
# 读取 Rclone 日志文件并提取校验和信息 
with open(log_file_path, 'rt', encoding='utf-8') as log_file, open(checksum_file_path, 'wt', encoding='utf-8') as checksum_file: 
 for line in log_file: 
  match = checksum_pattern.search(line)  
  if match:  
  # 提取文件名和校验和 
   file_name , _ , md5_checksum = match.groups()  
   # 写入到校验和文件中，格式为 "MD5SUM  FILENAME"  
   checksum_file.write(f'{md5_checksum} {file_name}\n') 
print(f'Generated checksum file: {checksum_file_path}')