.PHONY: help build up down restart logs migration migrate shell test clean

help:
	@echo "Available commands:"
	@echo "  make build       - Build Docker containers"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs"
	@echo "  make migration   - Create new migration"
	@echo "  make migrate     - Apply migrations"
	@echo "  make shell       - Open bot container shell"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f bot

migration:
	docker-compose exec bot alembic revision --autogenerate -m "$(name)"

migrate:
	docker-compose exec bot alembic upgrade head

shell:
	docker-compose exec bot bash

test:
	docker-compose exec bot pytest

clean:
	docker-compose down -v
	docker system prune -f