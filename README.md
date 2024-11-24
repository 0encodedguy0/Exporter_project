# Exporter_project

Для запуска системы:

1. Внесите необходимые данные в файлы:
    - main.py
    - Dockerfile
    - prometheus.yml
    - docker-compose.yml

2. Соберите и запустите контейнеры:
    ```bash
        docker-compose up --build
    ```

3. Убедитесь, что метрики доступны:
    - Откройте http://localhost:8000/metrics для проверки экспортера
    - Откройте http://localhost:9090 для интрефейса Prometheus
