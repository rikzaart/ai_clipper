#!/bin/bash

# Script untuk export YouTube cookies dari browser
# Untuk mengatasi YouTube bot detection

echo "============================================================"
echo "🍪 EXPORT YOUTUBE COOKIES"
echo "============================================================"
echo ""
echo "YouTube meminta verifikasi bot. Kita perlu export cookies dari browser."
echo ""
echo "📝 CARA 1: Otomatis (Recommended)"
echo "   yt-dlp sudah support --cookies-from-browser"
echo "   Agent akan otomatis coba cookies dari Chrome/Firefox/Safari"
echo ""
echo "   Yang perlu Anda lakukan:"
echo "   1. Buka YouTube di browser (Chrome/Firefox/Safari)"
echo "   2. Login ke akun YouTube"
echo "   3. Buka video yang ingin di-download"
echo "   4. Run agent lagi"
echo ""
echo "📝 CARA 2: Manual Export (Jika cara 1 gagal)"
echo ""
echo "   A. Install browser extension:"
echo "      Chrome: Get cookies.txt LOCALLY"
echo "      https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc"
echo ""
echo "      Firefox: cookies.txt"
echo "      https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/"
echo ""
echo "   B. Buka YouTube dan login"
echo ""
echo "   C. Click extension icon → Export cookies"
echo ""
echo "   D. Save as: cookies.txt di folder project ini"
echo ""
echo "   E. Update downloader.py untuk use cookies.txt:"
echo "      ydl_opts['cookiefile'] = 'cookies.txt'"
echo ""
echo "============================================================"
echo ""
echo "🔍 Checking browser cookies..."
echo ""

# Check if Chrome is installed
if [ -d "$HOME/Library/Application Support/Google/Chrome" ]; then
    echo "✅ Chrome detected"
    echo "   Cookies location: $HOME/Library/Application Support/Google/Chrome/Default/Cookies"
else
    echo "❌ Chrome not found"
fi

# Check if Firefox is installed
if [ -d "$HOME/Library/Application Support/Firefox" ]; then
    echo "✅ Firefox detected"
    echo "   Cookies location: $HOME/Library/Application Support/Firefox/Profiles/"
else
    echo "❌ Firefox not found"
fi

# Check if Safari is installed
if [ -d "$HOME/Library/Safari" ]; then
    echo "✅ Safari detected"
    echo "   Cookies location: $HOME/Library/Cookies/Cookies.binarycookies"
else
    echo "❌ Safari not found"
fi

echo ""
echo "============================================================"
echo "✅ Agent sudah dikonfigurasi untuk otomatis use browser cookies"
echo "   Pastikan Anda sudah login ke YouTube di browser"
echo "============================================================"

