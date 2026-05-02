#!/bin/zsh
set -e
cd /Users/antonzaritskyi/Desktop/project2
mkdir -p logs
mkdir -p ~/Library/LaunchAgents
cp launchd/com.worldfacts.commandbot.plist ~/Library/LaunchAgents/com.worldfacts.commandbot.plist
launchctl unload ~/Library/LaunchAgents/com.worldfacts.commandbot.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.worldfacts.commandbot.plist
launchctl start com.worldfacts.commandbot
echo "Command bot LaunchAgent installed and started: com.worldfacts.commandbot"
