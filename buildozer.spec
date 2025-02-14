[app]
title = MyApp
package.name = myapp
package.domain = org.example

# Исправление ошибки 1: Укажите исходную директорию
source.dir = .

# Исправление ошибки 2: Добавьте версию приложения
version = 1.0

# Остальные параметры
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,images/*,data/*
requirements = python3,kivy,telebot,sqlite3
orientation = portrait
log_level = 2

# Пути к SDK/NDK (должны совпадать с путями в workflow)
android.sdk_path = /home/runner/android-sdk
android.ndk_path = /home/runner/android-ndk
android.ndk = 25b
android.sdk = 34
android.build_tools = 34.0.0-rc5
