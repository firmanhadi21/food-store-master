import { defineConfig } from "vite";

// 日本版ビューアはデプロイしないので root を占有できる。
// GitHub Pages プロジェクトページなので base はリポジトリ名。
export default defineConfig({
  base: "/food-store-master/",
  define: {
    __BUILD_TIME__: JSON.stringify(
      new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC",
    ),
  },
});
