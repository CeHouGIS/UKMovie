/** @type {import('next').NextConfig} */
const isGitHubPages = process.env.GITHUB_ACTIONS === "true";
const isSitesBuild = process.env.SITES_BUILD === "true";
const basePath = isGitHubPages ? "/UKMovie" : "";

const nextConfig = {
  reactStrictMode: true,
  output: isSitesBuild ? "standalone" : "export",
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath
  }
};

export default nextConfig;
