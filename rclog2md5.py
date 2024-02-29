import re 
# 请根据你的实际日志文件路径修改下面的路径 
log_file_path = 'rclone.log' 
checksum_file_path = 'MD5SUMs.txt' 
# 正则表达式，用于从日志中匹配 MD5 校验和和文件名 
# 假设日志中的行格式为 "MD5 hash of file.txt: 12345abcdef67890" 
checksum_pattern = re.compile(r'DEBUG : ([^:]+): md5 = ([a-fA-F0-9]{32})') # DEBUG : idb/edfexport/Settings/Icu/ICU Waveforms.wks: md5 = 677975de6a15e03d0b88216d2b267c51 
# 读取 Rclone 日志文件并提取校验和信息 
with open(log_file_path, 'rt', encoding='utf-8') as log_file, open(checksum_file_path, 'wt', encoding='utf-8') as checksum_file: 
 for line in log_file: 
  match = checksum_pattern.search(line)  
  if match:  
  # 提取文件名和校验和 
   file_name, md5_checksum = match.groups()  
   # 写入到校验和文件中，格式为 "MD5SUM  FILENAME"  
   checksum_file.write(f'{md5_checksum} {file_name}\n') 
print(f'Generated checksum file: {checksum_file_path}')