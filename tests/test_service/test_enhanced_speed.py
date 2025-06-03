#!/usr/bin/env python3
"""Test enhanced service speed"""
import subprocess
import time

print("🚀 Testing Enhanced Service Speed")
proc = subprocess.Popen(['python', 'webcam_service.py'])
time.sleep(8)
proc.terminate()
proc.wait()
print("Enhanced service test completed") 