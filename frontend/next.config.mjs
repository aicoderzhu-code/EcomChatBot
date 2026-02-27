/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  transpilePackages: ['antd', '@ant-design/icons', '@ant-design/charts'],
  async rewrites() {
    const apiTarget = process.env.NODE_ENV === 'development'
      ? 'http://localhost:8000'
      : 'http://api:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiTarget}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
