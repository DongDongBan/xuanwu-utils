# from datetime import datetime
# from pydantic import BaseModel, validator

# class Span(BaseModel):
#     start: datetime
#     end: datetime

#     @validator('start')
#     def start_before_end(cls, start, values):
#         if 'end' in values and start >= values['end']:
#             raise ValueError('Start date must be before end date')
#         return start

# class Record(BaseModel):
#     file: str
#     span: Span
#     info: str

# class Seizure(BaseModel):
#     span: Span
#     info: str

# class PlotInfo(BaseModel):
#     record_lst: list[Record]
#     seizure_lst: list[Seizure]
#     unused_rec_idx_lst: list[int]



# # 加载 JSON 数据
# with open('./swecethz-plotinfo/ID01.json', 'r') as json_file:
#     json_data = json.load(json_file)

# # 进行数据验证
# try:
#     record_list = PlotInfo.model_validate(json_data)
#     print("JSON 数据有效")
# except Exception as e:
#     print("JSON 数据无效：", e)

import json
from jsonschema import validate

# 读取 JSON 数据和 JSON Schema
with open('./swecethz-plotinfo/ID01.json', 'r') as json_file:
    json_data = json.load(json_file)

with open('plotinfo.schema', 'r') as schema_file:
    schema = json.load(schema_file)

# 校验 JSON 数据
try:
    validate(json_data, schema)
    print("JSON 数据有效")
except Exception as e:
    print("JSON 数据无效：", e)