#!/bin/bash
# 清理历史中的API key：合并所有本地提交为一个干净提交
set -e
cd "$(dirname "$0")"

echo "========== 1. 软重置到远程状态 (保留文件修改) =========="
git reset --soft 8bba1d3

echo ""
echo "========== 2. 重新暂存所有文件 =========="
git add -A

echo ""
echo "========== 3. 验证密钥已移除 =========="
grep -r --exclude="git_push.sh" "sk-926" . 2>/dev/null && echo "⚠️ 密钥仍存在! 请检查!" && exit 1 || echo "✅ 无硬编码密钥"

echo ""
echo "========== 4. 提交 =========="
git commit -m "MIMO API迁移至DeepSeek (deepseek-v4-flash)"

echo ""
echo "========== 5. 强制推送 (覆盖旧历史) =========="
git push origin main --force-with-lease

echo ""
echo "========== ✅ 完成 =========="
git log --oneline -3
