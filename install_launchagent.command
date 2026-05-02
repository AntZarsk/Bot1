#!/bin/zsh
set -e
cd /Users/antonzaritskyi/Desktop/VS studio Code/project2
mkdir -p logs
mkdir -p ~/Library/LaunchAgents
cp launchd/com.worldfacts.bot.plist ~/Library/LaunchAgents/com.worldfacts.bot.plist
launchctl unload ~/Library/LaunchAgents/com.worldfacts.bot.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.worldfacts.bot.plist
launchctl start com.worldfacts.bot
echo "LaunchAgent installed and started: com.worldfacts.bot"
