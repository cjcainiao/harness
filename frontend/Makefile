# 前端常用命令

NPM := npm

.DEFAULT_GOAL := help
.PHONY: help install run build check format

help:
	@echo "install  安装依赖"
	@echo "run      开发模式启动（热重载）"
	@echo "build    构建产物（含类型检查）"
	@echo "check    类型检查"
	@echo "format   代码格式化"

install:
	$(NPM) install

run:
	$(NPM) run dev

build:
	$(NPM) run build

check:
	$(NPM) run type-check

format:
	$(NPM) run format
