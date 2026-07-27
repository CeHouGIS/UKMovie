# 英国影视取景地数据

生成日期：2026-07-26（UTC）

## 文件

- `uk_filming_locations.csv`：适合 Excel、数据库和数据分析。
- `uk_filming_locations.geojson`：适合 QGIS、ArcGIS、Mapbox、Kepler.gl。
- `wikipedia_uk_filming_categories.csv`：Wikipedia 社区分类补充表。
- `wikipedia_location_coordinates.csv`：社区分类地点的坐标映射和匹配来源。
- `wikipedia_uk_filming_categories_geocoded.csv`：已补充坐标的社区分类记录。
- `wikipedia_uk_filming_categories_geocoded.geojson`：网站使用的社区分类地图图层。
- `wikipedia_category_metadata.json`：社区分类补充表统计和许可。
- `metadata.json`：记录数量、生成时间和许可说明。
- `download_uk_filming_locations.py`：从 Wikidata 重新下载最新版数据。
- `download_wikipedia_uk_filming_categories.py`：重新下载 Wikipedia 分类数据。
- `uk_filming_work_catalog.csv`：按作品去重的名称、上映/首播日期和 IMDb ID目录。
- `uk_filming_film_catalog.csv`：严格电影类型目录，不含电视电影。
- `uk_filming_tv_catalog.csv`：电视剧、电视电影、季度、单集和特别节目目录。

## 数据范围

仅保留 Wikidata 中：

1. 作品被标记为电影、短片、动画片、电视电影、电视剧、迷你剧、网络剧、
   电视节目、电视剧单集、季度或特别节目；
2. 通过 `P915` 明确记录为实际拍摄地；
3. 地点的国家 `P17` 为英国；
4. 地点至少有坐标 `P625` 或地址 `P6375`。

记录数量以 `metadata.json` 中的最新结果为准。

另有一份开放的 Wikipedia 社区分类补充表，包含 8,614 条“作品—拍摄分类”
关系，涉及 6,443 个页面。分类名称能提供英国、构成国、城市、郡或制片厂级
位置，但通常没有精确坐标。该表采用 CC BY-SA 4.0，与 CC0 主表分开保存。

通过 Wikidata 与 GeoNames 英国地名包，目前已为其中 103 种分类地点匹配坐标，
覆盖 6,570 条作品—地点记录。补充坐标属于城市、地区或制片厂代表点，不能视为
摄影机精确机位。

## 时间码

`episode_timecode_start` 和 `episode_timecode_end` 已预留但为空。Wikidata
没有系统记录某个地点在影片中出现的分钟、秒数。时间码需要从字幕、视频内容、
剧本或人工核验中补充，不能由上映日期或取景地信息推断。

### 授权字幕管线

`download_subtitles.py` 使用 OpenSubtitles 官方 API，按主表中的 IMDb ID 搜索
授权账号可下载的英文字幕。脚本默认只做 dry-run；只有提供 `--execute` 时才访问
API，并默认最多搜索 20 部、下载 5 个文件。字幕正文、API 缓存和逐条对白索引
保存在被 Git 忽略的 `subtitle_output/`，不会提交或随网站发布。

```bash
python3 download_subtitles.py
python3 download_subtitles.py --execute --search-only
python3 download_subtitles.py --execute --max-searches 20 --max-downloads 5
```

`search_internet_archive_subtitles.py` 使用 Internet Archive 无密钥搜索 API，只匹配
`feature_films` 中明确标注 Public Domain 或 Creative Commons 且带 SRT/VTT 的
条目。字幕文件保存在 `subtitle_output/`，匹配元数据写入
`internet_archive_subtitle_matches.csv`。

## 注意

- `release_or_first_broadcast_date` 取该作品在 Wikidata 中记录的最早日期。
- 如果 Wikidata 只记录年份，日期可能表现为该年的 `01-01`，不表示作品一定在
  元旦上映。
- 有些地点是城市、郡或英国构成国，其坐标为区域中心点，并非具体摄影机机位。
- 本数据没有把剧情发生地当作拍摄地。
- Wikidata 结构化数据采用 CC0；仍建议在使用时注明数据来源为 Wikidata。

## 更新

```bash
cd /workplace/UKMovie
python3 download_uk_filming_locations.py
python3 download_wikipedia_uk_filming_categories.py
```
