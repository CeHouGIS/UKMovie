# 地名坐标补充源

下载日期：2026-07-26（UTC）

## GeoNames

- 文件：`geonames/GB.zip`
- 下载地址：<https://download.geonames.org/export/dump/GB.zip>
- 范围：英国地名、坐标及行政信息
- 许可：Creative Commons Attribution 4.0
- SHA-256：`84fc27d7d477489b006d334ac155794491c56bd47c852a910db24fb51684328a`

## OS Open Names

- 文件：`os_open_names/opennames_gb_csv.zip`
- 下载地址：<https://api.os.uk/downloads/v1/products/OpenNames/downloads?area=GB&format=CSV&redirect>
- 范围：英格兰、苏格兰和威尔士地名、道路编号与邮编
- 格式：CSV，压缩包约 104 MB
- 许可：OS OpenData Licence；压缩包内 `Doc/licence.txt` 亦有许可说明
- SHA-256：`eb2f84c5bd29dc3cd13afc05780f8665e5aedbf961d4c29184b768419fe19ba7`

OS Open Names 原始包超过 GitHub 单文件 100 MB 限制，因此保留在本地工作区，
不提交到仓库。脚本生成的匹配结果可以正常提交。

## 匹配结果

运行：

```bash
python3 enrich_wikipedia_locations.py
```

生成：

- `wikipedia_location_coordinates.csv`：122 种分类地点的坐标映射；
- `wikipedia_uk_filming_categories_geocoded.csv`：带坐标、坐标来源和精度说明的
  8,614 条民间分类记录。
- `wikipedia_uk_filming_categories_geocoded.geojson`：供网站地图直接加载的 6,570
  条已匹配记录。

当前有 103 种分类地点获得坐标，覆盖 6,570 条作品—地点记录和 4,882 个不同
Wikipedia 页面。未能可靠匹配的 19 种地点主要是已经停用、改名或同名的制片厂。
