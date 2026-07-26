import "./globals.css";

export const metadata = {
  title: "英国影视取景地图 | UK Movie Map",
  description: "探索英国境内电影与电视剧的开放取景地数据。"
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
