# 其他英国影视取景地来源评估

检索日期：2026-07-26

## 已并入主数据

### Wikidata 的细分作品类型

最初版本只查询了通用的“电影”和“电视剧”等类型，因此会漏掉 Wikidata
中只标记为短片、电视电影、迷你剧或具体电视剧单集的作品。最新版已经增加：

- 短片、无声短片和动画片
- 电视电影和两集电视电影
- 迷你剧和网络剧
- 电视剧单集的两种 Wikidata 类型
- 电视特别节目、Doctor Who serial、Christmas episode

扩展后由 2,497 条增加到 2,849 条，新增 352 条“作品—取景地”记录。

## 数据丰富但目前不宜直接批量复制

### ReelStreets（优先级很高）

- 2003 年开始由英国电影取景爱好者维护，持续接受用户提交的地点辨认和“现在”
  对照照片。
- 不只覆盖伦敦。其英国区域索引当前显示：London 各分页合计约 2,055 次影片
  收录；South East 约 1,902；South West 300；Midlands 126；North 260；
  Scotland 117；Wales 80；Northern Ireland 12。同一影片横跨多个区域时会
  重复，因此这些数字不能直接当作唯一作品数。
- 记录通常包括作品、电影截图、场景文字、辨认出的街道/建筑以及同机位现代照片。
- 很适合补充老英国电影和消失或改建的地点；经纬度并非每条都有，需要对地点名称
  另行地理编码。
- 没有找到开放数据许可或批量导出接口，建议先联系站方取得研究用途授权。
- https://www.reelstreets.com/films-listed-by-region/

### Ext.Street（最适合时间码）

- 民间维护的电影/电视剧地图，覆盖 London、Bath、Bristol、Oxford、Liverpool、
  Cornwall、Scotland、Wales 等许多英国地区。
- 单条场景同时包含作品年份、场景名称、影片时间码、地点文字、地图点和剧照。
- 例如《Hot Fuzz》页面记录了 `0:07:37` Peel House、`0:08:07` The Swan
  Hotel、`0:10:06` Wells Market Place、`0:55:03` St Cuthbert's Church 等。
- 用户提交表单本身要求填写 scene timestamp 和经纬度，字段结构与本项目非常匹配。
- 网站声明除影片剧照外的内容归 Ext Street Ltd 所有，没有公开批量复用许可；
  应先申请数据授权。
- https://www.extstreet.com/

### Find That Location

- 英国民间持续更新的电影、电视地点库，可按当前位置、地址或邮编搜索，并覆盖
  Dad's Army、Gavin and Stacey、Line of Duty、Still Game 等大量英国节目。
- 有节目、scene、location 和地图结构，并使用 TMDB/Digiguide 补节目资料。
- 条款明确限定：只可为个人非商业用途下载少量摘录；未经书面许可不得分发、
  商业利用或存入其他检索系统，所以没有批量抓取。
- https://findthatlocation.com/

### Doctor Who Locations Guide

- 专门由粉丝维护 Doctor Who、Torchwood 和 The Sarah Jane Adventures 在英国
  及海外的拍摄地点。
- 包含地点如何用于剧情、寻找方式、拍摄时与现在的对照，并持续记录拆除和改名。
- 对单集级补充非常有价值，但不是开放下载数据集。
- https://www.doctorwholocations.net/

### FilmingMap

- 民间全球地图，官网称覆盖 1,530 多部电影和电视剧；London 页面显示 198 部
  作品、1,059 个独立地点。
- 单条记录可到完整邮编级地址，例如 The IT Crowd 的地点记录。
- robots 文件明确禁止访问 `/api/`，也未提供开放导出许可，因此只作为候选来源。
- https://filmingmap.com/location/london-united-kingdom

### Filmaps

- 官网声称覆盖超过 20,000 部电影和电视剧。
- London 页面约有 778 个取景地。
- 提供地图位置，但未找到公开批量导出接口或开放数据许可。
- 地址：https://www.filmaps.com/

### SCEEN IT

- 全站显示约 8,154 个场景地点，London 专页显示 864 个地点。
- 有作品年份、地点、场景文字说明和剧照。
- 精确地址和 GPS 需要登录；未找到开放 API 或批量复用许可。
- 地址：https://www.sceen-it.com/special/london

### Where Was It Filmed

- 官网声称有超过 12,000 个全球取景地。
- 提供作品搜索和地图，但未找到公开导出或数据许可。
- 地址：https://www.wherewasfilmed.com/

### FilmedWhere

- 官网显示约 1,999 部电影，包含数千个已地理编码地点、场景说明和照片。
- 网站说明数据聚合自爱好者网站和其他数据库；未提供开放下载许可。
- 地址：https://www.filmedwhere.com/browse

### Movie-Locations.com

- 英国尤其是伦敦的老电影和经典电影覆盖较好，常有很具体的地点描述。
- 网站明确声明内容不得复制，除非取得书面许可，因此没有抓取。
- 地址：https://movie-locations.com/places/uk/gtrlondon.php

## 官方但不是可下载数据库

### VisitBritain / Visit Wales

- 有英国影视旅游地图和大量按作品编写的地点指南。
- 地点质量较高，但属于编辑内容，没有统一 CSV/API。
- 可作为人工校验和补充来源。
- https://www.visitbritain.com/en/things-to-do/top-filming-locations-britain-screen
- https://www.visitwales.com/things-do/attractions/tv-and-film-locations

### Screen Scotland

- “Made in Scotland”作品页面经常直接列出拍摄城镇和建筑。
- 另有面向制片方的 location image 数据库，但不是历史作品—地点开放数据集。
- https://www.screen.scot/film-in-scotland

## 关于分钟、秒时间码

上面的大型地点网站最多提供场景文字说明，通常也不提供可靠的影片时间码。
研究数据集 MovieNet、MAD 和 Movie Description Dataset 有视频片段或时间对齐，
但没有英国实际取景坐标，无法直接与本数据自动合并。建立时间码最可靠的方法仍是：

1. 先获得合法的视频文件和字幕；
2. 根据地点网站的场景说明检索字幕或剧本；
3. 对候选时间段抽帧；
4. 人工确认场景与地点；
5. 把开始、结束时间写入主 CSV 中预留的时间码列。

## 建议

如果需要显著超过当前 2,849 条，下一阶段应先向 Filmaps、SCEEN IT 或
Where Was It Filmed 申请 API/研究用途数据授权。拿到许可后，可以通过作品名、
年份、IMDb/TMDB ID 与当前 CC0 主表合并，并保留每条记录的来源和许可字段。
