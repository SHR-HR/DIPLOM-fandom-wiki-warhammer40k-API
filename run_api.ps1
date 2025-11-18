# Скрипт для запуска API через чистый Docker (без Docker Compose)
# Полезен для разработки и отладки

# Настройка поведения PowerShell при ошибках:
$ErrorActionPreference = "Stop"     # Останавливать выполнение при ошибках
$ProgressPreference = "SilentlyContinue"   # Не показывать прогресс-бары (для чистоты вывода)

# 1) Остановка и удаление существующего контейнера (если есть)
# 2>$null перенаправляет stderr в никуда, чтобы не видеть ошибок если контейнера нет
docker stop deep_lom_ka-api 2>$null
docker rm -f deep_lom_ka-api 2>$null

# 2) Сборка Docker образа с тегом deep_lom_ka-api
# Использует Dockerfile в текущей директории
docker build -t deep_lom_ka-api .

# 3) Запуск контейнера в фоновом режиме с параметрами:
# -d : detached (фоновый режим)
# --name : имя контейнера для удобного управления
# -p : проброс порта (хост:контейнер)
# -v : монтирование томов (хост:контейнер)
# --restart : политика перезапуска (Автоперезапуск при сбоях)
docker run -d --name deep_lom_ka-api `
  -p 8000:8000 `
  -v "$PSScriptRoot\data:/app/data" `
  --restart unless-stopped `
  deep_lom_ka-api

# 4) стримим логи в эту же консоль
Write-Host "`n--- Logs (Ctrl+C чтобы выйти; контейнер НЕ остановится) ---`n"
docker logs -f --tail=100 deep_lom_ka-api
