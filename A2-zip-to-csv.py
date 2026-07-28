import os
import zipfile
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd


# 加载环境变量
load_dotenv()
script_dir = Path(__file__).parent
zip_path_str = os.getenv("ZIP_SAVE_PATH")
csv_path_str = os.getenv("CSV_SAVE_PATH")

# 检查环境变量是否填写
if not zip_path_str or not csv_path_str:
    raise ValueError("请检查 .env 文件，ZIP_SAVE_PATH 和 CSV_SAVE_PATH 必须填写！")

# 确保 CSV 目录存在
zip_dir = script_dir / zip_path_str
csv_dir = script_dir / csv_path_str
csv_dir.mkdir(parents=True, exist_ok=True)

# 解压所有 ZIP 文件到 CSV 目录
for zip_file in zip_dir.glob("*.zip"):
    with zipfile.ZipFile(zip_file) as z:
        z.extractall(csv_dir) 

# 读取 CSV 文件
df = pd.read_csv(csv_dir / "amount-2026-6.csv")

# 查看数据信息
# print(type(df))                # 看类型——DataFrame
# print(df.shape)                # 几行几列
# print(df.columns)              # 所有列名
# print(df.head())               # 前 5 行
# print(df.dtypes)               # 每列的数据类型
# print(df["type"].unique())     # type 列有几种值
# print(df["model"].unique())    # 用到了哪些模型

# 转换为宽格式
df_wide = df.pivot_table(
    index=["user_id", "utc_date", "model"],
    columns="type",
    values="amount",
    aggfunc="sum"
).reset_index()

# 查看转换后的宽格式
# print(df_wide.head())
# print(df_wide.head())
# print(df_wide.columns)

# 读取价格映射
price_map = (
    df[["type", "price"]]         # 只取两列
    .drop_duplicates()            # 去重
    .dropna()                     # 去空值（去掉 request_count）
    .set_index("type")["price"]   # 设置 type 为索引，取 price 列
)
# print(price_map)


for col in price_map.index:
    df_wide[col] = df_wide[col] * price_map[col]


df_wide["total_cost"] = df_wide[price_map.index].sum(axis=1)


# 按模型汇总
result = df_wide.groupby("model")["total_cost"].sum().reset_index()
result.columns = ["模型", "总费用（元）"]
print("\n===== 费用汇总 =====")
print(result.to_string(index=False))

# 总计
print(f"\n总计: {result['总费用（元）'].sum():.4f} 元")

