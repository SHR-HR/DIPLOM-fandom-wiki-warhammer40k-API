# Скрипт для остановки и удаления контейнеров Docker Compose
# compose_down.ps1

# Команда docker compose down:
# - Останавливает запущенные контейнеры, определенные в docker-compose.yml
# - Удаляет остановленные контейнеры
# - Удаляет сети, созданные docker-compose (если не используются другие контейнеры)
docker compose down

