# Exporter_project
![398244519-192cf58a-c7a5-41eb-9c54-dca6e3f7a0b7](https://github.com/user-attachments/assets/1f74bd0e-9c7a-41a7-a71a-8e2740253c22)

## Для запуска системы:

1. Внесите необходимые данные в файлы:
    - main.py
    - Dockerfile
    - prometheus.yml
    - docker-compose.yml

2. Соберите и запустите контейнеры:
    ```bash
        docker-compose up --build
    ```

4. Убедитесь, что метрики доступны:
    - Откройте http://localhost:8000/metrics для проверки экспортера
    - Откройте http://localhost:9090 для интрефейса Prometheus
