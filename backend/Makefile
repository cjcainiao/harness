# 后端常用命令

UV := uv

.DEFAULT_GOAL := help
.PHONY: help install lock run start

help:
	@echo "install  安装依赖"
	@echo "lock     更新 uv.lock"
	@echo "run      开发模式启动（热重载）"
	@echo "start    启动服务"

install:
	$(UV) sync

lock:
	$(UV) lock

run:
	$(UV) run uvicorn app.main:app --reload

start:
	$(UV) run python -m app.main
