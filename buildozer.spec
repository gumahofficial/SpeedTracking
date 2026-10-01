[app]
title = SpeedTracking
package.name = speedtracking
package.domain = com.gumah
source.dir = .
source.include_exts = py,kv,png,jpg,atlas
version = 0.1
requirements = python3,kivy,numpy,opencv
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, INTERNET
android.api = 33
android.minapi = 21
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 0